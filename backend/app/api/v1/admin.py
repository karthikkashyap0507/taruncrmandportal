from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin", tags=["admin"])


class UserAdminResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    model_config = {"from_attributes": True}


class CompanyAdminResponse(BaseModel):
    id: int
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    job_count: int = 0
    model_config = {"from_attributes": True}


class AdminStats(BaseModel):
    total_users: int
    total_candidates: int
    total_recruiters: int
    total_companies: int
    total_jobs: int
    published_jobs: int
    total_applications: int


@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.platform_admin)),
):
    return AdminStats(
        total_users=db.query(User).count(),
        total_candidates=db.query(Candidate).count(),
        total_recruiters=db.query(Recruiter).count(),
        total_companies=db.query(Company).count(),
        total_jobs=db.query(Job).count(),
        published_jobs=db.query(Job).filter(Job.status == JobStatus.published).count(),
        total_applications=db.query(Application).count(),
    )


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.platform_admin)),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.offset(skip).limit(limit).all()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.platform_admin)),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()


@router.get("/companies", response_model=list[CompanyAdminResponse])
def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.platform_admin)),
):
    companies = db.query(Company).offset(skip).limit(limit).all()
    result = []
    for c in companies:
        job_count = db.query(Job).filter(Job.company_id == c.id).count()
        result.append(CompanyAdminResponse(
            id=c.id, name=c.name, website=c.website,
            industry=c.industry, job_count=job_count,
        ))
    return result


@router.delete("/companies/{company_id}", status_code=204)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.platform_admin)),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()


@router.get("/jobs")
def list_all_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.platform_admin)),
):
    jobs = db.query(Job).offset(skip).limit(limit).all()
    return [{"id": j.id, "title": j.title, "status": j.status, "company_id": j.company_id} for j in jobs]


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: int,
    status: JobStatus,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.platform_admin)),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = status
    db.commit()
    return {"message": "Status updated", "job_id": job_id, "status": status}
