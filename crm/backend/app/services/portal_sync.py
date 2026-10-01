"""
JobsNexGen Portal → CRM sync service.

Pulls data from the job portal's public/recruiter API and upserts it into the CRM
database. Portal records are matched to CRM records via the `portal_job_id` /
`portal_candidate_id` columns so repeated syncs update rather than duplicate.

Jobs are pulled from the portal's public `/jobs` endpoint (no auth). Applications
and candidates require a portal recruiter login, configured via
PORTAL_RECRUITER_EMAIL / PORTAL_RECRUITER_PASSWORD.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Application,
    Candidate,
    CandidateStatus,
    CRMJob,
    JobStatus,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── status mapping ──────────────────────────────────────────────────────────

# Portal JobStatus (draft/published/closed) → CRM JobStatus (open/on_hold/closed/filled)
_JOB_STATUS_MAP = {
    "published": JobStatus.open,
    "draft": JobStatus.on_hold,
    "closed": JobStatus.closed,
}

# Portal ApplicationStatus (applied/screening/interview/offered/rejected)
# → CRM Candidate pipeline stage / CandidateStatus
_APP_STAGE_MAP = {
    "applied": "applied",
    "screening": "screening",
    "interview": "interview",
    "offered": "offer",
    "rejected": "rejected",
}
_CAND_STATUS_MAP = {
    "applied": CandidateStatus.new,
    "screening": CandidateStatus.screening,
    "interview": CandidateStatus.interviewing,
    "offered": CandidateStatus.offered,
    "rejected": CandidateStatus.rejected,
}


def _parse_experience(level: str | None) -> float | None:
    """Best-effort '5 years' / '3+ years' → 5.0 / 3.0."""
    if not level:
        return None
    digits = "".join(c for c in level if c.isdigit() or c == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


# ── portal client ───────────────────────────────────────────────────────────

class PortalClient:
    def __init__(self) -> None:
        self.base = settings.PORTAL_API_URL.rstrip("/")
        self._token: str | None = None

    async def _login(self, client: httpx.AsyncClient) -> None:
        if not (settings.PORTAL_RECRUITER_EMAIL and settings.PORTAL_RECRUITER_PASSWORD):
            return
        resp = await client.post(
            f"{self.base}/auth/login",
            json={
                "email": settings.PORTAL_RECRUITER_EMAIL,
                "password": settings.PORTAL_RECRUITER_PASSWORD,
            },
        )
        resp.raise_for_status()
        self._token = resp.json().get("access_token")

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def fetch_jobs(self, client: httpx.AsyncClient) -> list[dict]:
        resp = await client.get(f"{self.base}/jobs", params={"limit": 200})
        resp.raise_for_status()
        return resp.json()

    async def fetch_recruiter_jobs(self, client: httpx.AsyncClient) -> list[dict]:
        resp = await client.get(f"{self.base}/jobs/recruiter/my", headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def fetch_applications(self, client: httpx.AsyncClient, job_id: int) -> list[dict]:
        resp = await client.get(
            f"{self.base}/jobs/{job_id}/applications", headers=self._auth_headers()
        )
        resp.raise_for_status()
        return resp.json()


# ── upsert helpers ──────────────────────────────────────────────────────────

async def _upsert_job(db: AsyncSession, pj: dict) -> tuple[CRMJob, bool]:
    """Insert or update a CRM job from a portal job dict. Returns (job, created)."""
    portal_id = pj["id"]
    existing = (
        await db.execute(select(CRMJob).where(CRMJob.portal_job_id == portal_id))
    ).scalar_one_or_none()

    company = pj.get("company") or {}
    fields = dict(
        title=pj.get("title") or "Untitled",
        client_name=company.get("name"),
        location=pj.get("location"),
        job_type=pj.get("employment_type") or "full-time",
        experience_min=_parse_experience(pj.get("experience_level")),
        salary_min=pj.get("salary_min"),
        salary_max=pj.get("salary_max"),
        skills_required=pj.get("skills") or [],
        description=pj.get("description"),
        status=_JOB_STATUS_MAP.get(str(pj.get("status")), JobStatus.open),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.updated_at = _utcnow()
        return existing, False

    job = CRMJob(portal_job_id=portal_id, source="portal", **fields)
    db.add(job)
    return job, True


async def _import_resume(client: httpx.AsyncClient | None, url: str | None, portal_cand_id) -> str | None:
    """Copy a resume from the portal (signed, short-lived link) into CRM private storage."""
    import os
    import uuid
    from app.core.files import canonical_url, content_matches, private_dir
    if not client or not url or not url.startswith("/api/v1/files/resumes/"):
        return None
    origin = settings.PORTAL_API_URL.split("/api/", 1)[0]
    ext = os.path.splitext(url.split("?", 1)[0])[1].lower()
    try:
        resp = await client.get(origin + url)
        if resp.status_code != 200 or len(resp.content) > 10 * 1024 * 1024 or not content_matches(resp.content, ext):
            return None
        filename = f"p{portal_cand_id}_{uuid.uuid4().hex}{ext}"
        with open(os.path.join(private_dir("resumes"), filename), "wb") as f:
            f.write(resp.content)
        return canonical_url("resumes", filename)
    except Exception:
        logger.exception("could not import resume for portal candidate %s", portal_cand_id)
        return None


async def _upsert_candidate(db: AsyncSession, app: dict, client: httpx.AsyncClient | None = None) -> Candidate:
    """Insert or update a CRM candidate from a portal application dict."""
    from app.services.dedupe import find_duplicates, normalize_email, normalize_phone
    info = app.get("candidate_info") or {}
    portal_cand_id = app.get("candidate_id")

    existing = None
    if portal_cand_id is not None:
        existing = (
            await db.execute(
                select(Candidate).where(Candidate.portal_candidate_id == portal_cand_id)
            )
        ).scalar_one_or_none()
    # Fall back to email/phone match so a candidate entered by hand isn't duplicated
    if not existing:
        dups = await find_duplicates(db, info.get("email"), app.get("phone"))
        existing = dups[0] if dups else None

    fields = dict(
        name=info.get("name") or app.get("full_name") or "Unknown",
        email=normalize_email(info.get("email")),
        phone=app.get("phone"),
        phone_normalized=normalize_phone(app.get("phone")),
        experience_years=float(app["years_experience"]) if app.get("years_experience") else None,
        skills=info.get("skills") or [],
        resume_url=None,  # filled below from a private copy (portal links expire)
        ats_score=int(app["score"]) if app.get("score") is not None else None,
        status=_CAND_STATUS_MAP.get(str(app.get("status")), CandidateStatus.new),
        source="portal",
        portal_candidate_id=portal_cand_id,
    )

    target = existing
    if existing:
        for k, v in fields.items():
            if v is not None or k in ("portal_candidate_id",):
                setattr(existing, k, v)
        existing.updated_at = _utcnow()
    else:
        target = Candidate(**fields)
        db.add(target)
    if not target.resume_url:
        target.resume_url = await _import_resume(client, info.get("resume_url") or app.get("resume_url"),
                                                 portal_cand_id)
    return target


async def _upsert_application(
    db: AsyncSession, crm_job: CRMJob, crm_cand: Candidate, app: dict
) -> bool:
    """Insert a CRM application linking job+candidate if not present. Returns created."""
    await db.flush()  # ensure job/candidate ids are populated
    existing = (
        await db.execute(
            select(Application).where(
                Application.job_id == crm_job.id,
                Application.candidate_id == crm_cand.id,
            )
        )
    ).scalar_one_or_none()

    stage = _APP_STAGE_MAP.get(str(app.get("status")), "applied")
    if existing:
        existing.stage = stage
        return False

    db.add(
        Application(
            job_id=crm_job.id,
            candidate_id=crm_cand.id,
            stage=stage,
            applied_at=_utcnow(),
        )
    )
    return True


# ── public entry points ─────────────────────────────────────────────────────

async def sync_jobs(db: AsyncSession) -> dict:
    """Pull all portal jobs and upsert into CRM. Returns counts."""
    client_obj = PortalClient()
    created = updated = 0
    async with httpx.AsyncClient(timeout=30) as client:
        jobs = await client_obj.fetch_jobs(client)
        for pj in jobs:
            _, was_created = await _upsert_job(db, pj)
            created += int(was_created)
            updated += int(not was_created)
        await db.commit()
    logger.info("Portal job sync: %d created, %d updated", created, updated)
    return {"source": "portal", "jobs_created": created, "jobs_updated": updated, "total": created + updated}


async def sync_applications(db: AsyncSession) -> dict:
    """Pull recruiter jobs + their applications, upserting candidates & applications."""
    if not (settings.PORTAL_RECRUITER_EMAIL and settings.PORTAL_RECRUITER_PASSWORD):
        return {
            "synced": False,
            "reason": "PORTAL_RECRUITER_EMAIL / PORTAL_RECRUITER_PASSWORD not configured",
        }

    client_obj = PortalClient()
    cand_created = app_created = 0
    async with httpx.AsyncClient(timeout=30) as client:
        await client_obj._login(client)
        rec_jobs = await client_obj.fetch_recruiter_jobs(client)
        for pj in rec_jobs:
            crm_job, _ = await _upsert_job(db, pj)
            await db.flush()
            apps = await client_obj.fetch_applications(client, pj["id"])
            for app in apps:
                before = await _count_candidates(db)
                crm_cand = await _upsert_candidate(db, app, client)
                await db.flush()
                after = await _count_candidates(db)
                cand_created += int(after > before)
                app_created += int(await _upsert_application(db, crm_job, crm_cand, app))
        await db.commit()
    logger.info(
        "Portal application sync: %d candidates, %d applications created",
        cand_created, app_created,
    )
    return {
        "synced": True,
        "candidates_created": cand_created,
        "applications_created": app_created,
    }


async def _count_candidates(db: AsyncSession) -> int:
    from sqlalchemy import func as _f
    return (await db.execute(select(_f.count(Candidate.id)))).scalar_one()
