"""Server-to-server feed for the JobsNexGen CRM.

The CRM runs on the same server and pulls every job and application changed
since its last sync. Two locks keep this private:
  * the shared INTEGRATION_KEY must be sent in the X-Integration-Key header, and
  * requests that came through the public website (nginx adds X-Forwarded-For /
    X-Real-IP) are refused, so the feed is only reachable from the server itself.
"""
import hmac
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.files import sign_resume_url
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.recruiter import Recruiter

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
        "created_at": j.created_at, "updated_at": j.updated_at,
    } for j in rows]}


@router.get("/job-ids", dependencies=[Guard])
def existing_job_ids(db: Session = Depends(get_db)):
    """Every job id that still exists, so the CRM can close jobs deleted on the portal."""
    return {"ids": [i for (i,) in db.query(Job.id).all()]}


@router.get("/applications", dependencies=[Guard])
def changed_applications(
    updated_since: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Application).options(joinedload(Application.candidate).joinedload(Candidate.user))
    if updated_since:
        q = q.filter(Application.updated_at >= updated_since)
    rows = q.order_by(Application.updated_at, Application.id).offset(skip).limit(limit).all()
    out = []
    for a in rows:
        cand = a.candidate
        user = cand.user if cand else None
        out.append({
            "id": a.id, "job_id": a.job_id, "candidate_id": a.candidate_id, "status": a.status.value,
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
