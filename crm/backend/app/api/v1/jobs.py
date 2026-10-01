from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner, require_owner_or_bdm
from app.core.security import utc
from app.models import (
    ActivityType, Application, ApplicationEvent, Candidate, CRMJob, Interview, InterviewStatus, InterviewType,
    JobStatus, NotifType, Placement, User, UserRole,
)
from app.services import ats
from app.services.activity import diff, log_activity, notify, queue_email

router = APIRouter(prefix="/jobs", tags=["crm-jobs"])


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company_id: Optional[int] = None
    client_name: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    job_type: Optional[str] = Field(default="full-time", max_length=50)
    experience_min: Optional[float] = Field(default=None, ge=0, le=60)
    experience_max: Optional[float] = Field(default=None, ge=0, le=60)
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    skills_required: Optional[List[str]] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=20000)
    positions: int = Field(default=1, ge=1, le=10000)
    status: JobStatus = JobStatus.open
    deadline: Optional[datetime] = None
    portal_job_id: Optional[int] = None
    assigned_to_id: Optional[int] = None

    @model_validator(mode="after")
    def ranges(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Minimum salary cannot be greater than maximum salary")
        if (self.experience_min is not None and self.experience_max is not None
                and self.experience_min > self.experience_max):
            raise ValueError("Minimum experience cannot be greater than maximum experience")
        return self


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    client_name: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    job_type: Optional[str] = Field(default=None, max_length=50)
    experience_min: Optional[float] = Field(default=None, ge=0, le=60)
    experience_max: Optional[float] = Field(default=None, ge=0, le=60)
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    skills_required: Optional[List[str]] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=20000)
    positions: Optional[int] = Field(default=None, ge=1, le=10000)
    status: Optional[JobStatus] = None
    deadline: Optional[datetime] = None
    assigned_to_id: Optional[int] = None


class ApplicationCreate(BaseModel):
    candidate_id: int
    stage: Optional[str] = "applied"
    notes: Optional[str] = Field(default=None, max_length=5000)


class InterviewCreate(BaseModel):
    candidate_id: int
    job_id: int
    type: InterviewType = InterviewType.video
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=5, le=600)
    interviewer_ids: Optional[List[int]] = None
    location_or_link: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=5000)


def _serialize_job(j: CRMJob) -> dict:
    return {
        "id": j.id,
        "title": j.title,
        "company_id": j.company_id,
        "client_name": j.client_name,
        "location": j.location,
        "job_type": j.job_type,
        "experience_min": j.experience_min,
        "experience_max": j.experience_max,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "skills_required": j.skills_required or [],
        "description": j.description,
        "positions": j.positions,
        "status": j.status.value,
        "deadline": j.deadline.isoformat() if j.deadline else None,
        "portal_job_id": j.portal_job_id,
        "assigned_to_id": j.assigned_to_id,
        "created_by_id": j.created_by_id,
        "created_at": j.created_at.isoformat(),
    }


def _serialize_application(a: Application, candidate: Candidate | None = None) -> dict:
    return {
        "id": a.id,
        "job_id": a.job_id,
        "candidate_id": a.candidate_id,
        "candidate_name": candidate.name if candidate else None,
        "candidate_email": candidate.email if candidate else None,
        "stage": a.stage,
        "notes": a.notes,
        "applied_at": a.applied_at.isoformat() if a.applied_at else None,
        "stage_changed_at": a.stage_changed_at.isoformat() if a.stage_changed_at else None,
        "created_at": a.created_at.isoformat(),
    }


def _serialize_interview(iv: Interview) -> dict:
    return {
        "id": iv.id,
        "candidate_id": iv.candidate_id,
        "job_id": iv.job_id,
        "application_id": iv.application_id,
        "type": iv.type.value,
        "scheduled_at": iv.scheduled_at.isoformat(),
        "duration_minutes": iv.duration_minutes,
        "status": iv.status.value,
        "location_or_link": iv.location_or_link,
        "notes": iv.notes,
        "feedback": iv.feedback,
        "rating": iv.rating,
    }


async def _get_job(db: AsyncSession, job_id: int) -> CRMJob:
    job = await db.get(CRMJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


async def _staff_ids(db: AsyncSession, roles: tuple) -> list[int]:
    rows = await db.execute(select(User.id).where(User.role.in_(roles), User.is_active == True))  # noqa: E712
    return [r[0] for r in rows.all()]


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(CRMJob)
    if status:
        query = query.where(CRMJob.status == status)
    if search:
        query = query.where(CRMJob.title.ilike(f"%{search}%") | CRMJob.client_name.ilike(f"%{search}%"))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    rows = (await db.execute(query.order_by(CRMJob.created_at.desc()).offset((page - 1) * limit).limit(limit))).scalars()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize_job(j) for j in rows.all()]}


@router.post("/", status_code=201)
async def create_job(payload: JobCreate, request: Request, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_owner_or_bdm)):
    job = CRMJob(**payload.model_dump(exclude_none=True), created_by_id=current_user.id)
    db.add(job)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Created job {job.title}", "job", job.id, request=request)
    notify(db, [job.assigned_to_id], "Job assigned to you", job.title, NotifType.task_assigned,
           f"/jobs/{job.id}", exclude=current_user.id)
    await db.commit()
    await db.refresh(job)
    return _serialize_job(job)


@router.get("/interviews/all")
async def list_interviews(
    upcoming_only: bool = False,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Interview)
    if upcoming_only:
        q = q.where(Interview.scheduled_at >= datetime.now(timezone.utc))
    rows = (await db.execute(q.order_by(Interview.scheduled_at.asc()).limit(limit))).scalars().all()
    return [_serialize_interview(iv) for iv in rows]


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = await _get_job(db, job_id)
    data = _serialize_job(job)
    # Only the columns the page needs: avoids building thousands of full ORM objects
    rows = (await db.execute(
        select(Application.id, Application.candidate_id, Application.stage, Application.notes,
               Application.applied_at, Application.stage_changed_at, Application.created_at,
               Candidate.name, Candidate.email)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .where(Application.job_id == job_id).order_by(Application.id.desc())
    )).all()
    iso = lambda d: d.isoformat() if d else None  # noqa: E731
    data["applications"] = [{
        "id": r.id, "job_id": job_id, "candidate_id": r.candidate_id, "candidate_name": r.name,
        "candidate_email": r.email, "stage": r.stage, "notes": r.notes, "applied_at": iso(r.applied_at),
        "stage_changed_at": iso(r.stage_changed_at), "created_at": iso(r.created_at),
    } for r in rows]
    return data


@router.put("/{job_id}")
async def update_job(job_id: int, payload: JobUpdate, request: Request, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_owner_or_bdm)):
    job = await _get_job(db, job_id)
    data = payload.model_dump(exclude_none=True)
    smin, smax = data.get("salary_min", job.salary_min), data.get("salary_max", job.salary_max)
    if smin is not None and smax is not None and smin > smax:
        raise HTTPException(422, "Minimum salary cannot be greater than maximum salary")
    changes = diff(job, data)
    for field, val in data.items():
        setattr(job, field, val)
    job.updated_at = datetime.now(timezone.utc)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated job {job.title}", "job", job.id,
                     changes=changes, request=request)
    if "assigned_to_id" in changes:
        notify(db, [job.assigned_to_id], "Job assigned to you", job.title, NotifType.task_assigned,
               f"/jobs/{job.id}", exclude=current_user.id)
    await db.commit()
    return _serialize_job(job)


@router.delete("/{job_id}")
async def delete_job(job_id: int, request: Request, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_owner)):
    job = await _get_job(db, job_id)
    if (await db.execute(select(func.count()).select_from(Placement).where(Placement.job_id == job.id))).scalar():
        raise HTTPException(409, "This job has placements linked to billing and can't be deleted. Close it instead.")
    for iv in (await db.execute(select(Interview).where(Interview.job_id == job.id))).scalars().all():
        await db.delete(iv)
    log_activity(db, current_user, ActivityType.delete, f"Deleted job {job.title}", "job", job.id, request=request)
    await db.delete(job)
    await db.commit()
    return {"message": "Job deleted"}


# ── Applications (ATS) ────────────────────────────────────────────────────────

@router.post("/{job_id}/applications", status_code=201)
async def add_application(job_id: int, payload: ApplicationCreate, request: Request,
                          db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = await _get_job(db, job_id)
    candidate = await db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    stage = payload.stage or "applied"
    if stage not in ats.STAGES or stage in ("hired", "withdrawn"):
        raise HTTPException(422, "New applications start at applied, screening, interview or offer")
    existing = (await db.execute(select(Application).where(
        Application.job_id == job_id, Application.candidate_id == candidate.id))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"{candidate.name} is already in the pipeline for this job")
    app = Application(job_id=job_id, candidate_id=candidate.id, stage=stage, notes=payload.notes,
                      applied_at=datetime.now(timezone.utc), stage_changed_at=datetime.now(timezone.utc))
    db.add(app)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"{candidate.name} is already in the pipeline for this job")
    db.add(ApplicationEvent(application_id=app.id, from_stage=None, to_stage=stage, actor_id=current_user.id))
    log_activity(db, current_user, ActivityType.create, f"Added {candidate.name} to {job.title}", "application",
                 app.id, request=request)
    await db.commit()
    await db.refresh(app)
    return _serialize_application(app, candidate)


@router.patch("/{job_id}/applications/{app_id}/stage")
async def update_application_stage(
    job_id: int,
    app_id: int,
    stage: str,
    request: Request,
    note: Optional[str] = Query(None, max_length=2000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = (await db.execute(select(Application).where(Application.id == app_id, Application.job_id == job_id))
           ).scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    job = await _get_job(db, job_id)
    candidate = await db.get(Candidate, app.candidate_id)
    old = ats.change_stage(db, app, stage, current_user.id, note)
    if candidate and stage in ats.CANDIDATE_STATUS_FOR_STAGE:
        candidate.status = ats.CANDIDATE_STATUS_FOR_STAGE[stage]
        candidate.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.status_change,
                 f"{candidate.name if candidate else 'Candidate'} on {job.title}: {old} -> {stage}",
                 "application", app.id, changes={"stage": {"from": old, "to": stage}}, request=request)
    recipients = [candidate.created_by_id if candidate else None, job.assigned_to_id]
    if stage == "hired":
        recipients += await _staff_ids(db, (UserRole.owner, UserRole.bdm))
    notify(db, recipients, f"{candidate.name if candidate else 'Candidate'} moved to {stage}",
           f"{job.title}: {old} -> {stage}" + (" - record the placement for billing" if stage == "hired" else ""),
           NotifType.application_stage, f"/jobs/{job.id}", exclude=current_user.id)
    await db.commit()
    if candidate and candidate.email and stage in ("interview", "offer", "hired"):
        from app.services.email import send_candidate_status_email
        await queue_email(send_candidate_status_email, candidate.email, candidate.name,
                          {"offer": "offer extended"}.get(stage, stage), job.title)
    return _serialize_application(app, candidate)


@router.get("/{job_id}/applications/{app_id}/history")
async def application_history(job_id: int, app_id: int, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    app = (await db.execute(select(Application).where(Application.id == app_id, Application.job_id == job_id))
           ).scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    rows = (await db.execute(select(ApplicationEvent).where(ApplicationEvent.application_id == app_id)
                             .order_by(ApplicationEvent.id))).scalars().all()
    return [{"from_stage": e.from_stage, "to_stage": e.to_stage, "actor_id": e.actor_id, "note": e.note,
             "created_at": e.created_at.isoformat()} for e in rows]


# ── Interviews ────────────────────────────────────────────────────────────────

@router.post("/interviews", status_code=201)
async def schedule_interview(payload: InterviewCreate, request: Request, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    cand = await db.get(Candidate, payload.candidate_id)
    if not cand:
        raise HTTPException(404, "Candidate not found")
    job = await _get_job(db, payload.job_id)
    if utc(payload.scheduled_at) < datetime.now(timezone.utc):
        raise HTTPException(422, "The interview time must be in the future")
    app = (await db.execute(select(Application).where(
        Application.job_id == job.id, Application.candidate_id == cand.id))).scalar_one_or_none()
    interviewers = []
    if payload.interviewer_ids:
        interviewers = list((await db.execute(
            select(User).where(User.id.in_(payload.interviewer_ids), User.is_active == True)  # noqa: E712
        )).scalars().all())
    interviewer_ids = [u.id for u in interviewers]
    iv = Interview(
        interviewers=interviewers,
        candidate_id=cand.id,
        job_id=job.id,
        application_id=app.id if app else None,
        type=payload.type,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        location_or_link=payload.location_or_link,
        notes=payload.notes,
        status=InterviewStatus.scheduled,
        scheduled_by_id=current_user.id,
    )
    db.add(iv)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Interview scheduled: {cand.name} for {job.title}",
                 "interview", iv.id, request=request)
    notify(db, [*interviewer_ids, cand.created_by_id, job.assigned_to_id],
           f"Interview scheduled: {cand.name}", f"{job.title} on {payload.scheduled_at:%d %b %Y %H:%M}",
           NotifType.interview_scheduled, "/interviews", exclude=current_user.id)
    await db.commit()
    await db.refresh(iv)
    if cand.email:
        from app.services.email import send_interview_scheduled_email
        await queue_email(send_interview_scheduled_email, cand.email, cand.name, iv, job.title)
    return _serialize_interview(iv)


@router.patch("/interviews/{interview_id}")
async def update_interview(
    interview_id: int,
    request: Request,
    status: Optional[InterviewStatus] = None,
    feedback: Optional[str] = Query(None, max_length=5000),
    rating: Optional[int] = Query(None, ge=1, le=5),
    scheduled_at: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    iv = await db.get(Interview, interview_id)
    if not iv:
        raise HTTPException(404, "Interview not found")
    before = {"status": iv.status.value, "scheduled_at": iv.scheduled_at.isoformat()}
    change = None
    if scheduled_at and utc(scheduled_at) != utc(iv.scheduled_at):
        if utc(scheduled_at) < datetime.now(timezone.utc):
            raise HTTPException(422, "The new interview time must be in the future")
        iv.scheduled_at = scheduled_at
        iv.status = InterviewStatus.rescheduled
        iv.reminder_sent_at = None
        change = "rescheduled"
    if status:
        if status == InterviewStatus.cancelled and iv.status != InterviewStatus.cancelled:
            change = "cancelled"
        iv.status = status
    if feedback:
        iv.feedback = feedback
    if rating is not None:
        iv.rating = rating
    log_activity(db, current_user, ActivityType.update, f"Interview #{iv.id} updated", "interview", iv.id,
                 changes={"before": before, "after": {"status": iv.status.value,
                                                     "scheduled_at": iv.scheduled_at.isoformat()}},
                 request=request)
    cand = await db.get(Candidate, iv.candidate_id)
    if change:
        interviewer_ids = [u.id for u in (await db.run_sync(lambda s: list(iv.interviewers)))]
        notify(db, [*interviewer_ids, cand.created_by_id if cand else None],
               f"Interview {change}: {cand.name if cand else ''}",
               f"Now {iv.scheduled_at:%d %b %Y %H:%M}" if change == "rescheduled" else "The interview was cancelled",
               NotifType.interview_updated, "/interviews", exclude=current_user.id)
    await db.commit()
    if change and cand and cand.email:
        from app.services.email import send_interview_updated_email
        await queue_email(send_interview_updated_email, cand.email, cand.name, iv, change)
    return _serialize_interview(iv)
