from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import CRMJob, Application, Candidate, User, JobStatus, Interview, InterviewStatus, InterviewType

router = APIRouter(prefix="/jobs", tags=["crm-jobs"])


class JobCreate(BaseModel):
    title: str
    company_id: Optional[int] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = "full-time"
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    skills_required: Optional[List[str]] = None
    description: Optional[str] = None
    positions: int = 1
    status: JobStatus = JobStatus.open
    deadline: Optional[datetime] = None
    portal_job_id: Optional[int] = None
    assigned_to_id: Optional[int] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    skills_required: Optional[List[str]] = None
    description: Optional[str] = None
    positions: Optional[int] = None
    status: Optional[JobStatus] = None
    deadline: Optional[datetime] = None
    assigned_to_id: Optional[int] = None


class ApplicationCreate(BaseModel):
    candidate_id: int
    stage: Optional[str] = "applied"
    notes: Optional[str] = None


class InterviewCreate(BaseModel):
    candidate_id: int
    job_id: int
    type: InterviewType = InterviewType.video
    scheduled_at: datetime
    duration_minutes: int = 60
    interviewer_ids: Optional[List[int]] = None
    location_or_link: Optional[str] = None
    notes: Optional[str] = None


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


def _serialize_application(a: Application) -> dict:
    return {
        "id": a.id,
        "job_id": a.job_id,
        "candidate_id": a.candidate_id,
        "stage": a.stage,
        "notes": a.notes,
        "applied_at": a.applied_at.isoformat() if a.applied_at else None,
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


@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    search: Optional[str] = Query(None),
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(CRMJob)
    if status:
        query = query.where(CRMJob.status == status)
    if search:
        query = query.where(CRMJob.title.ilike(f"%{search}%") | CRMJob.client_name.ilike(f"%{search}%"))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    result = await db.execute(query.order_by(CRMJob.created_at.desc()).offset((page - 1) * limit).limit(limit))
    return {"total": total, "page": page, "limit": limit, "data": [_serialize_job(j) for j in result.scalars().all()]}


@router.post("/", status_code=201)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = CRMJob(**payload.model_dump(exclude_none=True), created_by_id=current_user.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return _serialize_job(job)


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(CRMJob).where(CRMJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    data = _serialize_job(job)

    apps_result = await db.execute(select(Application).where(Application.job_id == job_id))
    data["applications"] = [_serialize_application(a) for a in apps_result.scalars().all()]
    return data


@router.put("/{job_id}")
async def update_job(job_id: int, payload: JobUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(CRMJob).where(CRMJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(job, field, val)
    await db.commit()
    return _serialize_job(job)


@router.delete("/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(CRMJob).where(CRMJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    await db.delete(job)
    await db.commit()
    return {"message": "Job deleted"}


@router.post("/{job_id}/applications", status_code=201)
async def add_application(
    job_id: int,
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = Application(
        job_id=job_id,
        candidate_id=payload.candidate_id,
        stage=payload.stage,
        notes=payload.notes,
        applied_at=datetime.now(timezone.utc),
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return _serialize_application(application)


@router.patch("/{job_id}/applications/{app_id}/stage")
async def update_application_stage(
    job_id: int,
    app_id: int,
    stage: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Application).where(Application.id == app_id, Application.job_id == job_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    app.stage = stage
    await db.commit()
    return _serialize_application(app)


@router.get("/interviews/all")
async def list_interviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Interview).order_by(Interview.scheduled_at.asc()))
    return [_serialize_interview(iv) for iv in result.scalars().all()]


@router.post("/interviews", status_code=201)
async def schedule_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    iv = Interview(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
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
    if payload.interviewer_ids:
        users_result = await db.execute(select(User).where(User.id.in_(payload.interviewer_ids)))
        iv.interviewers = list(users_result.scalars().all())
    await db.commit()
    await db.refresh(iv)

    try:
        from app.services.email import send_interview_scheduled_email
        cand_result = await db.execute(select(Candidate).where(Candidate.id == payload.candidate_id))
        cand = cand_result.scalar_one_or_none()
        if cand and cand.email:
            send_interview_scheduled_email(cand.email, cand.name, iv)
    except Exception:
        pass

    return _serialize_interview(iv)


@router.patch("/interviews/{interview_id}")
async def update_interview(
    interview_id: int,
    status: Optional[InterviewStatus] = None,
    feedback: Optional[str] = None,
    rating: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    iv = result.scalar_one_or_none()
    if not iv:
        raise HTTPException(404, "Interview not found")
    if status:
        iv.status = status
    if feedback:
        iv.feedback = feedback
    if rating is not None:
        iv.rating = rating
    await db.commit()
    return _serialize_interview(iv)
