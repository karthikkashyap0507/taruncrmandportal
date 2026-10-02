"""Server-to-server feed for the JobsNexGen CRM.

The CRM runs on the same server and pulls every job and application changed
since its last sync. Two locks keep this private:
  * the shared INTEGRATION_KEY must be sent in the X-Integration-Key header, and
  * requests that came through the public website (nginx adds X-Forwarded-For /
    X-Real-IP) are refused, so the feed is only reachable from the server itself.
"""
import hmac
import secrets
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.files import sign_resume_url
from app.auth.security import hash_password
from app.models.application import Application, ApplicationStatus
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.job import EDUCATION_LEVELS, Job, JobStatus
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.services import ats
from app.services.audit import audit
from app.services.job_rules import parse_min_years

router = APIRouter(prefix="/integrations/crm", tags=["integrations"], include_in_schema=False)


def require_integration_key(request: Request, x_integration_key: str | None = Header(None)) -> None:
    if request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip"):
        raise HTTPException(status_code=404, detail="Not found")
    if not settings.INTEGRATION_KEY:
        raise HTTPException(status_code=503, detail="CRM integration is not configured (INTEGRATION_KEY)")
    if not x_integration_key or not hmac.compare_digest(x_integration_key, settings.INTEGRATION_KEY):
        raise HTTPException(status_code=403, detail="Invalid integration key")


Guard = Depends(require_integration_key)


def _period(job: Job) -> str | None:
    return job.salary_period or ("year" if (job.salary_min or job.salary_max) else None)


@router.get("/jobs", dependencies=[Guard])
def changed_jobs(
    updated_since: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Jobs in every status (drafts and ones awaiting approval too), oldest change first."""
    q = db.query(Job).options(joinedload(Job.company), joinedload(Job.recruiter).joinedload(Recruiter.user))
    if updated_since:
        q = q.filter(Job.updated_at >= updated_since)
    rows = q.order_by(Job.updated_at, Job.id).offset(skip).limit(limit).all()
    return {"data": [{
        "id": j.id, "title": j.title, "description": j.description, "status": j.status.value,
        "company": j.company.name if j.company else None,
        "posted_by": j.recruiter.user.name if j.recruiter and j.recruiter.user else None,
        "posted_by_email": j.recruiter.user.email if j.recruiter and j.recruiter.user else None,
        "location": j.location, "locality": j.locality, "education": j.education,
        "salary_min": j.salary_min, "salary_max": j.salary_max, "salary_period": _period(j),
        "skills": j.skills or [], "experience_level": j.experience_level, "employment_type": j.employment_type,
        "is_premium": bool(j.is_premium), "source": j.source or "portal", "crm_job_id": j.crm_job_id,
        "expires_at": j.expires_at, "created_at": j.created_at, "updated_at": j.updated_at,
    } for j in rows]}


@router.get("/job-ids", dependencies=[Guard])
def existing_job_ids(db: Session = Depends(get_db)):
    """Every job id that still exists, so the CRM can close jobs deleted on the portal."""
    return {"ids": [i for (i,) in db.query(Job.id).all()]}


@router.get("/applications", dependencies=[Guard])
def changed_applications(
    updated_since: datetime | None = None,
    job_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Application).options(joinedload(Application.candidate).joinedload(Candidate.user),
                                      joinedload(Application.job))
    if updated_since:
        q = q.filter(Application.updated_at >= updated_since)
    if job_id is not None:
        q = q.filter(Application.job_id == job_id)
    rows = q.order_by(Application.updated_at, Application.id).offset(skip).limit(limit).all()
    out = []
    for a in rows:
        cand = a.candidate
        user = cand.user if cand else None
        out.append({
            "id": a.id, "job_id": a.job_id, "candidate_id": a.candidate_id, "status": a.status.value,
            "job_is_premium": bool(a.job.is_premium) if a.job else False,
            "applied_at": a.applied_at, "updated_at": a.updated_at,
            "name": a.full_name or (user.name if user else None),
            "email": user.email if user else None,
            "phone": a.phone,
            "years_experience": a.years_experience,
            "education": a.education,
            "expected_salary": a.expected_salary,
            "current_location": a.current_location,
            "headline": cand.headline if cand else None,
            "skills": (cand.skills if cand else None) or [],
            "score": a.score,
            # short-lived signed link so the CRM can keep its own private copy
            "resume_url": sign_resume_url(a.resume_url or (cand.resume_url if cand else None)),
        })
    return {"data": out}


# ── CRM -> portal ─────────────────────────────────────────────────────────────

SYSTEM_EMAIL = "crm-jobs@jobsnexgen.system"


def _system_recruiter(db: Session) -> Recruiter:
    """The account CRM-published jobs are posted under. It can't sign in (random password) and
    has no mailbox; the HR team works the applicants in the CRM."""
    user = db.query(User).filter(User.email == SYSTEM_EMAIL).first()
    if not user:
        user = User(name="JobsNexGen Recruitment", email=SYSTEM_EMAIL, role=UserRole.recruiter,
                    password_hash=hash_password(secrets.token_urlsafe(32)), is_active=True)
        db.add(user)
        db.flush()
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        home = db.query(Company).filter(Company.external_ref == "jobsnexgen").first()
        if not home:
            home = Company(name="JobsNexGen", external_ref="jobsnexgen")
            db.add(home)
            db.flush()
        recruiter = Recruiter(user_id=user.id, company_id=home.id)
        db.add(recruiter)
        db.flush()
    return recruiter


def _client_company(db: Session, crm_company_id: int | None, name: str | None) -> Company:
    """The portal company shown on a CRM job. It is kept separate from employers' own company
    accounts (matched by external_ref), so no employer login can edit or read these jobs."""
    label = (name or "").strip() or "JobsNexGen Client"
    ref = f"crm-company:{crm_company_id}" if crm_company_id else f"crm-name:{label.lower()[:80]}"
    company = db.query(Company).filter(Company.external_ref == ref).first()
    if not company:
        company = Company(name=label, external_ref=ref)
        db.add(company)
        db.flush()
    elif company.name != label:
        company.name = label
    return company


_CRM_STATUS = {"open": JobStatus.published, "on_hold": JobStatus.draft, "closed": JobStatus.closed,
               "filled": JobStatus.closed}


class CRMJobIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=20000)
    client_name: Optional[str] = Field(default=None, max_length=255)
    crm_company_id: Optional[int] = None
    location: Optional[str] = Field(default=None, max_length=255)
    locality: Optional[str] = Field(default=None, max_length=120)
    education: Optional[str] = None
    salary_min: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    salary_max: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    salary_period: Optional[Literal["month", "year"]] = None
    skills: list[str] = Field(default_factory=list, max_length=100)
    experience_level: Optional[str] = Field(default=None, max_length=100)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    status: Literal["open", "on_hold", "closed", "filled"] = "open"
    expires_at: Optional[datetime] = None

    @field_validator("education")
    @classmethod
    def known_education(cls, v):
        if v in (None, ""):
            return None
        if v not in EDUCATION_LEVELS:
            raise ValueError(f"education must be one of: {', '.join(EDUCATION_LEVELS)}")
        return v


def _utc_naive(dt: datetime | None) -> datetime | None:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt and dt.tzinfo else dt


@router.put("/jobs/by-crm/{crm_job_id}", dependencies=[Guard])
def upsert_crm_job(crm_job_id: int, body: CRMJobIn, request: Request, db: Session = Depends(get_db)):
    """Create or update the public job for a CRM job. CRM jobs are client jobs, so they are
    premium and go live without the employer approval step. Returns the portal job id."""
    job = db.query(Job).filter(Job.crm_job_id == crm_job_id).first()
    company = _client_company(db, body.crm_company_id, body.client_name)
    has_salary = body.salary_min is not None or body.salary_max is not None
    fields = dict(
        title=body.title.strip(),
        description=(body.description or "").strip() or body.title.strip(),
        company_id=company.id,
        location=(body.location or "").strip() or None,
        locality=(body.locality or "").strip() or None,
        education=body.education,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        salary_period=(body.salary_period or "month") if has_salary else None,
        skills=[s.strip()[:60] for s in body.skills if s and s.strip()][:50],
        experience_level=body.experience_level,
        experience_min_years=parse_min_years(body.experience_level),
        employment_type=(body.employment_type or "full_time").replace("-", "_"),
        status=_CRM_STATUS[body.status],
        expires_at=_utc_naive(body.expires_at),
        is_premium=True,
        source="crm",
    )
    now = datetime.now(timezone.utc)
    created = job is None
    if created:
        recruiter = _system_recruiter(db)
        job = Job(crm_job_id=crm_job_id, recruiter_id=recruiter.id, created_at=now, approved_at=now, **fields)
        db.add(job)
    else:
        for key, value in fields.items():
            setattr(job, key, value)
        if job.approved_at is None:
            job.approved_at = now
    db.flush()
    audit(db, "integration.crm_job_published" if created else "integration.crm_job_updated",
          entity_type="job", entity_id=job.id, details={"crm_job_id": crm_job_id, "status": job.status.value},
          request=request)
    db.commit()
    return {"id": job.id, "status": job.status.value, "created": created}


class StatusIn(BaseModel):
    status: ApplicationStatus
    note: Optional[str] = Field(default=None, max_length=2000)


@router.post("/applications/{application_id}/status", dependencies=[Guard])
def set_application_status(application_id: int, body: StatusIn, request: Request, db: Session = Depends(get_db)):
    """A stage change made in the CRM. Same rules as the recruiter dashboard (no moving back,
    hired needs an offer); the candidate is emailed as usual."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status == body.status:
        return {"id": app.id, "status": app.status.value, "changed": False}
    # Staff record a withdrawal on the candidate's behalf (e.g. they phoned to say so)
    ats.change_status(db, app, body.status, None, body.note or "Updated in the CRM",
                      by_candidate=body.status == ApplicationStatus.withdrawn)
    audit(db, "integration.crm_status_changed", entity_type="application", entity_id=app.id,
          details={"to": body.status.value}, request=request)
    db.commit()
    from app.api.v1.jobs import _notify_status
    _notify_status(db, app, body.status.value)
    return {"id": app.id, "status": app.status.value, "changed": True}


class PortalJobStatusIn(BaseModel):
    status: Literal["open", "closed"]


@router.post("/jobs/{job_id}/status", dependencies=[Guard])
def set_portal_job_status(job_id: int, body: PortalJobStatusIn, request: Request, db: Session = Depends(get_db)):
    """Close or reopen a premium portal job from the CRM (e.g. the client's position is filled).
    The employer's job text is never changed from the CRM; reopening needs an earlier approval."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if body.status == "closed":
        job.status = JobStatus.closed
    elif job.approved_at is None:
        raise HTTPException(status_code=409, detail="This job hasn't been approved on the portal yet")
    else:
        job.status = JobStatus.published
    audit(db, "integration.crm_job_status", entity_type="job", entity_id=job.id,
          details={"to": job.status.value}, request=request)
    db.commit()
    return {"id": job.id, "status": job.status.value}
