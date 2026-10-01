from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from datetime import datetime

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.saved_job import SavedJob
from app.models.user import User
from app.schemas.job import CompanyResponse, JobResponse

router = APIRouter(prefix="/saved-jobs", tags=["saved-jobs"])


class SavedJobResponse(BaseModel):
    id: int
    job_id: int
    saved_at: datetime
    job: JobResponse

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SavedJobResponse])
def list_saved_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(SavedJob, Job)
        .join(Job, Job.id == SavedJob.job_id)
        .options(joinedload(Job.company))
        .filter(SavedJob.user_id == user.id)
        .order_by(SavedJob.saved_at.desc())
        .all()
    )
    result = []
    for s, job in rows:
        result.append(SavedJobResponse(
            id=s.id,
            job_id=s.job_id,
            saved_at=s.saved_at,
            job=JobResponse(
                id=job.id,
                company_id=job.company_id,
                recruiter_id=job.recruiter_id,
                title=job.title,
                description=job.description,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                skills=job.skills,
                experience_level=job.experience_level,
                location=job.location,
                employment_type=job.employment_type,
                status=job.status,
                company=CompanyResponse.model_validate(job.company) if job.company else None,
            ),
        ))
    return result


@router.post("/{job_id}", status_code=201)
def save_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.status == JobStatus.published).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = db.query(SavedJob).filter(SavedJob.user_id == user.id, SavedJob.job_id == job_id).first()
    if existing:
        return {"message": "Already saved", "job_id": job_id}
    saved = SavedJob(user_id=user.id, job_id=job_id)
    db.add(saved)
    db.commit()
    return {"message": "Job saved", "job_id": job_id}


@router.delete("/{job_id}", status_code=200)
def unsave_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    saved = db.query(SavedJob).filter(SavedJob.user_id == user.id, SavedJob.job_id == job_id).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Not saved")
    db.delete(saved)
    db.commit()
    return {"message": "Job unsaved", "job_id": job_id}


@router.get("/check/{job_id}")
def check_saved(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    saved = db.query(SavedJob).filter(SavedJob.user_id == user.id, SavedJob.job_id == job_id).first()
    return {"saved": saved is not None}
