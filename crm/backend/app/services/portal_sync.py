"""
JobsNexGen job portal <-> CRM sync.

Uses the portal's private CRM API (/integrations/crm/*, shared PORTAL_INTEGRATION_KEY).

CRM -> portal (pushed as soon as something is saved; retried by the scheduler if
the portal can't be reached):
* CRM jobs marked "publish on portal" are created/updated as public, premium jobs.
  Closing, filling or un-publishing one closes it on the portal.
* Pipeline stage changes on portal applicants update the portal application, so
  the candidate sees the same status (the portal emails them).
* Closing a premium job that came from the portal closes it there too.

Portal -> CRM (pulled every PORTAL_SYNC_INTERVAL_SECONDS and on "Sync now"):
* Only premium portal jobs (a client pays JobsNexGen) come into the CRM; free ones
  stay on the portal. A job that is made free again is closed in the CRM.
  Live = "open", awaiting approval/draft = "on hold", rejected/closed = "closed".
  A CRM user's own status choice is kept until the status changes on the portal.
* Applicants to those jobs become CRM candidates (de-duplicated by portal id,
  email or phone) with a pipeline entry; resumes are copied into CRM storage.
* Jobs deleted on the portal are closed in the CRM.
"""
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Application, Candidate, CandidateStatus, Company, CRMJob, JobStatus, NotifType, SyncState, User, UserRole,
)

# CRM pipeline stage -> portal application status
_PORTAL_STATUS = {
    "applied": "applied", "screening": "screening", "interview": "interview", "offer": "offered",
    "hired": "hired", "rejected": "rejected", "withdrawn": "withdrawn",
}

logger = logging.getLogger(__name__)

PAGE = 500
OVERLAP = timedelta(minutes=2)  # re-read the last two minutes so slow commits on the portal aren't missed
_lock = asyncio.Lock()

_JOB_STATUS = {
    "published": JobStatus.open,
    "pending": JobStatus.on_hold,
    "draft": JobStatus.on_hold,
    "rejected": JobStatus.closed,
    "closed": JobStatus.closed,
}
_STAGE = {
    "applied": "applied", "screening": "screening", "interview": "interview", "offered": "offer",
    "hired": "hired", "rejected": "rejected", "withdrawn": "withdrawn",
}
_NEW_CANDIDATE_STATUS = {
    "applied": CandidateStatus.new, "screening": CandidateStatus.screening,
    "interview": CandidateStatus.interviewing, "offered": CandidateStatus.offered,
    "hired": CandidateStatus.placed, "rejected": CandidateStatus.rejected, "withdrawn": CandidateStatus.rejected,
}


def configured() -> bool:
    return bool(settings.PORTAL_INTEGRATION_KEY)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value) -> datetime | None:
    """Portal timestamps arrive as ISO strings in UTC (with or without an offset)."""
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _naive(dt: datetime | None) -> datetime | None:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt and dt.tzinfo else dt


def _first_number(text: str | None) -> float | None:
    """'3-5 years' -> 3.0, '5+ years' -> 5.0."""
    m = re.search(r"\d+(?:\.\d+)?", text or "")
    return float(m.group()) if m else None


def _salary_text(amount: int | None) -> str | None:
    return f"₹{amount:,}/month" if amount else None


# ── portal feed ───────────────────────────────────────────────────────────────

class PortalFeed:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.base = settings.PORTAL_API_URL.rstrip("/")

    async def rows(self, path: str, since: datetime | None):
        skip = 0
        while True:
            params = {"skip": skip, "limit": PAGE}
            if since:
                params["updated_since"] = since.isoformat()
            resp = await self.client.get(f"{self.base}{path}", params=params)
            resp.raise_for_status()
            batch = resp.json()["data"]
            for row in batch:
                yield row
            if len(batch) < PAGE:
                return
            skip += PAGE

    async def job_ids(self) -> set[int]:
        resp = await self.client.get(f"{self.base}/integrations/crm/job-ids")
        resp.raise_for_status()
        return set(resp.json()["ids"])


# ── upserts ───────────────────────────────────────────────────────────────────

async def _upsert_job(db: AsyncSession, pj: dict, clients: dict[str, int]) -> tuple[CRMJob | None, bool, bool]:
    """Returns (job, created, just_went_live); job is None for a free job the CRM doesn't track.
    Sets job._newly_tracked when the CRM starts following it (so its earlier applicants are fetched)."""
    job = (await db.execute(select(CRMJob).where(CRMJob.portal_job_id == pj["id"]))).scalars().first()
    created = _parse_ts(pj.get("created_at"))
    if job is not None and job.portal_created_at and created and abs(
            (_naive(job.portal_created_at) - created).total_seconds()) > 2:
        # The portal reused the id of a job that was deleted: this is a different job
        _detach(job)
        job = None
    if job is None and pj.get("crm_job_id"):
        # A job the CRM published itself: link it, never create a second copy. If this sync can't
        # see it (just created, or deleted in the CRM), leave it alone; the push records the link.
        job = await db.get(CRMJob, pj["crm_job_id"])
        if job is None:
            return None, False, False
        job._newly_tracked = job.portal_job_id != pj["id"]
        job.portal_job_id = pj["id"]
    if job is not None:
        job.portal_created_at = created
    if job is not None and (job.source or "crm") != "portal":
        # The CRM owns this job's details; just remember what the portal shows
        job.portal_status, job.portal_premium = pj.get("status"), True
        return job, False, False
    premium = bool(pj.get("is_premium"))
    if not premium:
        if job is not None and job.portal_premium is not False:
            job.portal_premium = False
            if job.status in (JobStatus.open, JobStatus.on_hold):
                job.status = JobStatus.closed
            job.updated_at = _now()
        return job, False, False
    poster = pj.get("posted_by")
    if poster and pj.get("posted_by_email"):
        poster = f"{poster} ({pj['posted_by_email']})"
    fields = dict(
        title=(pj.get("title") or "Untitled")[:255],
        client_name=pj.get("company"),
        location=pj.get("location"),
        locality=pj.get("locality"),
        education=pj.get("education"),
        job_type=(pj.get("employment_type") or "full_time").replace("_", "-"),
        experience_min=_first_number(pj.get("experience_level")),
        salary_min=pj.get("salary_min"),
        salary_max=pj.get("salary_max"),
        salary_period=pj.get("salary_period"),
        skills_required=pj.get("skills") or [],
        description=pj.get("description"),
        posted_by=poster,
    )
    portal_status = pj.get("status") or "published"
    client_id = clients.get((pj.get("company") or "").strip().lower())
    if job:
        for key, value in fields.items():
            setattr(job, key, value)
        went_live = False
        if job.portal_premium is False:  # upgraded to premium: take the portal's status again
            job.portal_status = None
            job._newly_tracked = True
        job.portal_premium = True
        if portal_status != job.portal_status:
            new_status = _JOB_STATUS.get(portal_status, JobStatus.on_hold)
            went_live = new_status == JobStatus.open and job.status != JobStatus.open
            job.status, job.portal_status = new_status, portal_status
        if job.company_id is None and client_id:
            job.company_id = client_id
        job.updated_at = _now()
        return job, False, went_live
    job = CRMJob(portal_job_id=pj["id"], source="portal", portal_status=portal_status, portal_premium=True,
                 portal_created_at=created,
                 publish_on_portal=False, status=_JOB_STATUS.get(portal_status, JobStatus.on_hold),
                 company_id=client_id, **fields)
    job._newly_tracked = True
    db.add(job)
    return job, True, job.status == JobStatus.open


def _detach(job: CRMJob) -> None:
    """Stop tracking a portal job that no longer exists (closing it if it was still active)."""
    job.portal_job_id, job.portal_status, job.updated_at = None, "deleted", _now()
    if job.status in (JobStatus.open, JobStatus.on_hold):
        job.status = JobStatus.closed


async def _import_resume(client: httpx.AsyncClient, url: str | None, portal_cand_id) -> str | None:
    """Copy a resume from the portal (signed, short-lived link) into CRM private storage."""
    from app.core.files import canonical_url, content_matches, private_dir
    if not url or not url.startswith("/api/v1/files/resumes/"):
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


async def _upsert_candidate(db: AsyncSession, pa: dict, client: httpx.AsyncClient) -> tuple[Candidate, bool]:
    """Match on portal id, then email/phone; fill in blanks without overwriting CRM edits."""
    from app.services.dedupe import find_duplicates, normalize_email, normalize_phone
    portal_id = pa.get("candidate_id")
    cand = None
    if portal_id is not None:
        cand = (await db.execute(select(Candidate).where(Candidate.portal_candidate_id == portal_id))).scalars().first()
    if not cand:
        dups = await find_duplicates(db, pa.get("email"), pa.get("phone"))
        cand = dups[0] if dups else None

    details = dict(
        email=normalize_email(pa.get("email")),
        phone=(pa.get("phone") or None) and pa["phone"][:20],
        phone_normalized=normalize_phone(pa.get("phone")),
        experience_years=float(pa["years_experience"]) if pa.get("years_experience") is not None else None,
        location=pa.get("current_location"),
        expected_salary=_salary_text(pa.get("expected_salary")),
        education=pa.get("education"),
        current_title=pa.get("headline"),
        skills=pa.get("skills") or None,
        ats_score=int(pa["score"]) if pa.get("score") is not None else None,
    )
    created = cand is None
    if created:
        cand = Candidate(name=(pa.get("name") or "Portal candidate")[:120], source="portal",
                         portal_candidate_id=portal_id,
                         status=_NEW_CANDIDATE_STATUS.get(pa.get("status"), CandidateStatus.new),
                         **{k: v for k, v in details.items() if v is not None})
        db.add(cand)
    else:
        for key, value in details.items():
            if value is not None and getattr(cand, key) in (None, "", []):
                setattr(cand, key, value)
        if cand.portal_candidate_id is None:
            cand.portal_candidate_id = portal_id
        cand.updated_at = _now()
    if not cand.resume_url:
        cand.resume_url = await _import_resume(client, pa.get("resume_url"), portal_id)
    return cand, created


async def _upsert_application(db: AsyncSession, job: CRMJob, cand: Candidate, pa: dict) -> bool:
    """Create or update the pipeline entry. Returns True if it was created."""
    from app.services.ats import CANDIDATE_STATUS_FOR_STAGE
    app = (await db.execute(select(Application).where(Application.portal_application_id == pa["id"]))).scalars().first()
    if app is not None and app.job_id != job.id:
        app.portal_application_id = None  # the portal reused the id of a deleted application
        app = None
    if not app:
        app = (await db.execute(select(Application).where(
            Application.job_id == job.id, Application.candidate_id == cand.id))).scalars().first()
    portal_status = pa.get("status") or "applied"
    stage = _STAGE.get(portal_status, "applied")
    if app is None:
        db.add(Application(job_id=job.id, candidate_id=cand.id, stage=stage, stage_changed_at=_now(),
                           applied_at=_parse_ts(pa.get("applied_at")) or _now(),
                           portal_application_id=pa["id"], portal_status=portal_status))
        return True
    app.portal_application_id = pa["id"]
    if portal_status != app.portal_status:
        app.stage, app.stage_changed_at, app.portal_status = stage, _now(), portal_status
        if stage in CANDIDATE_STATUS_FOR_STAGE:
            cand.status = CANDIDATE_STATUS_FOR_STAGE[stage]
    return False


# ── entry points ──────────────────────────────────────────────────────────────

async def _state(db: AsyncSession) -> SyncState:
    state = await db.get(SyncState, "portal")
    if not state:
        state = SyncState(name="portal")
        db.add(state)
        await db.flush()
    return state


async def _staff(db: AsyncSession) -> list[int]:
    return [r[0] for r in (await db.execute(select(User.id).where(
        User.role.in_([UserRole.owner, UserRole.bdm]), User.is_active == True))).all()]  # noqa: E712


async def run_sync(db: AsyncSession, full: bool = False) -> dict:
    """Pull everything that changed on the portal. Safe to call any time; runs one at a time."""
    if not configured():
        return {"configured": False,
                "message": "Portal sync is not set up: PORTAL_INTEGRATION_KEY is missing on the CRM server."}
    from app.services.activity import notify

    async with _lock:
        started = _now()
        result = {"configured": True, "jobs_created": 0, "jobs_updated": 0, "jobs_closed_deleted": 0,
                  "free_jobs_skipped": 0, "candidates_created": 0, "applications_created": 0,
                  "applications_updated": 0, "applications_skipped": 0, "jobs_pushed": 0, "statuses_pushed": 0,
                  "push_failures": 0}
        try:
            state = await _state(db)
            jobs_since = None if full or not state.jobs_cursor else _naive(state.jobs_cursor) - OVERLAP
            apps_since = None if full or not state.applications_cursor else _naive(state.applications_cursor) - OVERLAP
            jobs_cursor, apps_cursor = _naive(state.jobs_cursor), _naive(state.applications_cursor)
            clients = {name.strip().lower(): cid for cid, name in (await db.execute(select(Company.id, Company.name))).all()
                       if name}
            live_jobs: list[CRMJob] = []
            new_apps: list[tuple[CRMJob, Candidate]] = []
            newly_tracked: list[int] = []
            jobs_by_portal: dict[int, CRMJob | None] = {}
            hold_cursor: datetime | None = None  # earliest applicant we couldn't place yet

            async def handle_application(pa: dict, client: httpx.AsyncClient) -> bool:
                """Upsert one portal application. Returns False if its job isn't in the CRM (yet)."""
                pid = pa["job_id"]
                if pid not in jobs_by_portal:
                    jobs_by_portal[pid] = (await db.execute(
                        select(CRMJob).where(CRMJob.portal_job_id == pid))).scalars().first()
                job = jobs_by_portal[pid]
                if job is None or job.portal_premium is False:  # free jobs' applicants stay on the portal
                    result["applications_skipped"] += 1
                    return not pa.get("job_is_premium")
                cand, cand_created = await _upsert_candidate(db, pa, client)
                await db.flush()
                result["candidates_created"] += int(cand_created)
                if await _upsert_application(db, job, cand, pa):
                    result["applications_created"] += 1
                    new_apps.append((job, cand))
                else:
                    result["applications_updated"] += 1
                await db.flush()
                return True

            async with httpx.AsyncClient(timeout=30, headers={"X-Integration-Key": settings.PORTAL_INTEGRATION_KEY}) as client:
                feed = PortalFeed(client)
                result.update(await push_pending(db, client))
                async for pj in feed.rows("/integrations/crm/jobs", jobs_since):
                    job, created, went_live = await _upsert_job(db, pj, clients)
                    if job is None:
                        result["free_jobs_skipped"] += 1
                    else:
                        result["jobs_created" if created else "jobs_updated"] += 1
                        if getattr(job, "_newly_tracked", False):
                            newly_tracked.append(pj["id"])
                    if went_live:
                        live_jobs.append(job)
                    ts = _parse_ts(pj.get("updated_at"))
                    if ts and (jobs_cursor is None or ts > jobs_cursor):
                        jobs_cursor = ts
                await db.flush()

                existing = await feed.job_ids()
                for job in (await db.execute(select(CRMJob).where(
                        CRMJob.portal_job_id.isnot(None), CRMJob.source == "portal"))).scalars().all():
                    if job.portal_job_id not in existing:
                        result["jobs_closed_deleted"] += int(job.status in (JobStatus.open, JobStatus.on_hold))
                        _detach(job)
                await db.flush()

                async for pa in feed.rows("/integrations/crm/applications", apps_since):
                    ts = _parse_ts(pa.get("updated_at"))
                    if not await handle_application(pa, client) and ts:
                        hold_cursor = ts if hold_cursor is None or ts < hold_cursor else hold_cursor
                    if ts and (apps_cursor is None or ts > apps_cursor):
                        apps_cursor = ts
                # Jobs the CRM just started following: bring in their earlier applicants too
                for pid in dict.fromkeys(newly_tracked):
                    async for pa in feed.rows(f"/integrations/crm/applications?job_id={pid}", None):
                        await handle_application(pa, client)
                if hold_cursor is not None and (apps_cursor is None or hold_cursor < apps_cursor):
                    apps_cursor = hold_cursor - timedelta(seconds=1)

            # In-app alerts: new live jobs for owners/BDMs, new applicants for the job's recruiter
            if live_jobs:
                staff = await _staff(db)
                if len(live_jobs) <= 5:
                    for job in live_jobs:
                        notify(db, staff, f"New job from the portal: {job.title}",
                               job.client_name or "Posted on the job portal", NotifType.system, f"/jobs/{job.id}")
                else:
                    notify(db, staff, f"{len(live_jobs)} new jobs from the portal", "Open the Jobs page to review them",
                           NotifType.system, "/jobs")
            for job, cand in new_apps:
                if job.assigned_to_id:
                    notify(db, [job.assigned_to_id], f"New applicant: {cand.name}", f"Applied on the portal for {job.title}",
                           NotifType.candidate_update, f"/jobs/{job.id}")

            state.jobs_cursor, state.applications_cursor = jobs_cursor, apps_cursor
            state.last_run_at = state.last_success_at = started
            state.last_error, state.last_result = None, result
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.exception("portal sync failed")
            state = await _state(db)
            state.last_run_at, state.last_error = started, f"{type(exc).__name__}: {exc}"[:1000]
            await db.commit()
            raise
    if any(v for k, v in result.items() if k != "configured"):
        logger.info("portal sync: %s", result)
    return result


async def status(db: AsyncSession) -> dict:
    state = await db.get(SyncState, "portal")
    portal_jobs = (await db.execute(select(func.count(CRMJob.id)).where(CRMJob.portal_job_id.isnot(None)))).scalar_one()
    open_portal_jobs = (await db.execute(select(func.count(CRMJob.id)).where(
        CRMJob.portal_job_id.isnot(None), CRMJob.status == JobStatus.open))).scalar_one()
    portal_cands = (await db.execute(select(func.count(Candidate.id)).where(
        Candidate.portal_candidate_id.isnot(None)))).scalar_one()
    published = (await db.execute(select(func.count(CRMJob.id)).where(
        CRMJob.source != "portal", CRMJob.portal_job_id.isnot(None), CRMJob.status == JobStatus.open))).scalar_one()
    waiting = (await db.execute(select(func.count(CRMJob.id)).where(CRMJob.portal_push_pending == True))).scalar_one()  # noqa: E712
    return {
        "configured": configured(),
        "interval_seconds": settings.PORTAL_SYNC_INTERVAL_SECONDS,
        "last_run_at": state.last_run_at if state else None,
        "last_success_at": state.last_success_at if state else None,
        "last_error": state.last_error if state else None,
        "last_result": state.last_result if state else None,
        "synced_jobs": portal_jobs,
        "open_portal_jobs": open_portal_jobs,
        "synced_candidates": portal_cands,
        "published_crm_jobs": published,
        "waiting_to_publish": waiting,
        "portal_url": settings.PORTAL_PUBLIC_URL.rstrip("/"),
    }


# ── CRM -> portal pushes ──────────────────────────────────────────────────────

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=20, headers={"X-Integration-Key": settings.PORTAL_INTEGRATION_KEY})


def _error_text(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            detail = exc.response.json().get("detail")
        except ValueError:
            detail = exc.response.text[:200]
        return f"HTTP {exc.response.status_code}: {detail}"
    return f"{type(exc).__name__}: {exc}"[:500]


def _job_payload(job: CRMJob) -> dict:
    status = job.status.value if job.publish_on_portal else "closed"
    deadline = job.deadline.isoformat() if job.deadline else None
    exp = f"{job.experience_min:g}+ years" if job.experience_min else ("Fresher" if job.experience_min == 0 else None)
    if job.experience_min is not None and job.experience_max:
        exp = f"{job.experience_min:g}-{job.experience_max:g} years"
    return {
        "title": job.title, "description": job.description, "client_name": job.client_name,
        "crm_company_id": job.company_id, "location": job.location, "locality": job.locality,
        "education": job.education,
        "salary_min": int(job.salary_min) if job.salary_min is not None else None,
        "salary_max": int(job.salary_max) if job.salary_max is not None else None,
        "salary_period": job.salary_period or ("month" if (job.salary_min or job.salary_max) else None),
        "skills": job.skills_required or [], "experience_level": exp,
        "employment_type": (job.job_type or "full-time").replace("-", "_"), "status": status,
        "expires_at": deadline,
    }


def needs_push(job: CRMJob) -> bool:
    """CRM jobs are published (or kept closed) on the portal; portal jobs only get status changes."""
    if (job.source or "crm") == "portal":
        return job.portal_job_id is not None
    return bool(job.publish_on_portal) or job.portal_job_id is not None


async def push_job(db: AsyncSession, job: CRMJob, client: httpx.AsyncClient | None = None) -> bool:
    """Send one job to the portal now. On failure it stays pending and the scheduler retries."""
    if not configured() or not needs_push(job):
        job.portal_push_pending = False
        return True
    own = client is None
    client = client or _client()
    base = settings.PORTAL_API_URL.rstrip("/")
    try:
        if (job.source or "crm") == "portal":
            target = "open" if job.status == JobStatus.open else ("closed" if job.status in (JobStatus.closed, JobStatus.filled) else None)
            if target:
                resp = await client.post(f"{base}/integrations/crm/jobs/{job.portal_job_id}/status", json={"status": target})
                resp.raise_for_status()
                job.portal_status = resp.json()["status"]
        else:
            resp = await client.put(f"{base}/integrations/crm/jobs/by-crm/{job.id}", json=_job_payload(job))
            resp.raise_for_status()
            data = resp.json()
            job.portal_job_id, job.portal_status, job.portal_premium = data["id"], data["status"], True
        job.portal_push_pending, job.portal_push_error = False, None
        return True
    except httpx.HTTPError as exc:
        job.portal_push_pending, job.portal_push_error = True, _error_text(exc)
        logger.warning("could not publish job %s to the portal: %s", job.id, job.portal_push_error)
        return False
    finally:
        if own:
            await client.aclose()


async def push_application_status(app: Application, client: httpx.AsyncClient | None = None) -> tuple[str, str | None]:
    """Send a pipeline stage to the portal. Returns ("ok"|"refused"|"pending", message)."""
    if not configured() or not app.portal_application_id:
        return "ok", None
    target = _PORTAL_STATUS.get(app.stage)
    if not target or target == app.portal_status:
        app.portal_push_pending = False
        return "ok", None
    own = client is None
    client = client or _client()
    try:
        resp = await client.post(
            f"{settings.PORTAL_API_URL.rstrip('/')}/integrations/crm/applications/{app.portal_application_id}/status",
            json={"status": target, "note": "Updated in the CRM"})
        if resp.status_code in (404, 409, 422):
            try:
                msg = resp.json().get("detail")
            except ValueError:
                msg = resp.text[:200]
            app.portal_push_pending, app.portal_push_error = False, str(msg)
            return "refused", str(msg)
        resp.raise_for_status()
        app.portal_status, app.portal_push_pending, app.portal_push_error = resp.json()["status"], False, None
        return "ok", None
    except httpx.HTTPError as exc:
        app.portal_push_pending, app.portal_push_error = True, _error_text(exc)
        return "pending", app.portal_push_error
    finally:
        if own:
            await client.aclose()


async def push_pending(db: AsyncSession, client: httpx.AsyncClient) -> dict:
    """Retry everything that couldn't be sent to the portal earlier."""
    pushed = statuses = failed = 0
    for job in (await db.execute(select(CRMJob).where(CRMJob.portal_push_pending == True))).scalars().all():  # noqa: E712
        if await push_job(db, job, client):
            pushed += 1
        else:
            failed += 1
    for app in (await db.execute(select(Application).where(Application.portal_push_pending == True))).scalars().all():  # noqa: E712
        state, _ = await push_application_status(app, client)
        statuses += state == "ok"
        failed += state == "pending"
    await db.flush()
    return {"jobs_pushed": pushed, "statuses_pushed": statuses, "push_failures": failed}
