from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.candidate import Candidate
from app.auth.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.job import CompanyResponse, JobResponse

router = APIRouter(prefix="/external", tags=["external-jobs"])


class ExternalJob(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    employment_type: Optional[str] = None
    redirect_url: str
    source: str = "adzuna"


class JobSearchResponse(BaseModel):
    internal: list[JobResponse]
    external: list[ExternalJob]
    total: int


@router.get("/jobs", response_model=JobSearchResponse)
async def search_all_jobs(
    q: str = Query("", description="Search query"),
    location: str = Query("", description="Location"),
    employment_type: str = Query("", description="Employment type"),
    salary_min: int = Query(0, description="Min salary"),
    db: Session = Depends(get_db),
):
    # Internal jobs
    query = db.query(Job).options(joinedload(Job.company)).filter(Job.status == JobStatus.published)
    if q:
        query = query.filter(Job.title.ilike(f"%{q}%") | Job.description.ilike(f"%{q}%"))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if employment_type:
        query = query.filter(Job.employment_type.ilike(f"%{employment_type}%"))
    if salary_min:
        query = query.filter(Job.salary_min >= salary_min)

    internal_jobs_raw = query.limit(20).all()
    internal_jobs = [
        JobResponse(
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
        )
        for job in internal_jobs_raw
    ]

    # External jobs via Adzuna
    external_jobs = []
    if settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY:
        try:
            search_q = q or "software developer"
            search_loc = location or "india"
            url = (
                f"https://api.adzuna.com/v1/api/jobs/in/search/1"
                f"?app_id={settings.ADZUNA_APP_ID}"
                f"&app_key={settings.ADZUNA_APP_KEY}"
                f"&results_per_page=10"
                f"&what={search_q}"
                f"&where={search_loc}"
                f"&content-type=application/json"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        sal_min = r.get("salary_min")
                        sal_max = r.get("salary_max")
                        external_jobs.append(ExternalJob(
                            id=str(r.get("id", "")),
                            title=r.get("title", ""),
                            company=r.get("company", {}).get("display_name", "Unknown"),
                            location=r.get("location", {}).get("display_name", ""),
                            description=r.get("description", "")[:500],
                            salary_min=float(sal_min) if sal_min else None,
                            salary_max=float(sal_max) if sal_max else None,
                            employment_type=r.get("contract_time", ""),
                            redirect_url=r.get("redirect_url", ""),
                            source="adzuna",
                        ))
        except Exception:
            pass

    return JobSearchResponse(
        internal=internal_jobs,
        external=external_jobs,
        total=len(internal_jobs) + len(external_jobs),
    )


@router.get("/recommendations", response_model=list[JobResponse])
def get_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return jobs that match the candidate's skills."""
    if user.role != UserRole.candidate:
        return []
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate or not candidate.skills:
        # Return latest published jobs as fallback
        jobs = db.query(Job).options(joinedload(Job.company)).filter(
            Job.status == JobStatus.published
        ).order_by(Job.id.desc()).limit(6).all()
    else:
        skills = candidate.skills[:5]
        jobs = db.query(Job).options(joinedload(Job.company)).filter(
            Job.status == JobStatus.published
        ).all()
        # Score jobs by matching skills
        scored = []
        for job in jobs:
            job_skills_lower = [s.lower() for s in (job.skills or [])]
            matches = sum(1 for s in skills if s.lower() in job_skills_lower or s.lower() in job.title.lower())
            scored.append((matches, job))
        scored.sort(key=lambda x: x[0], reverse=True)
        jobs = [j for _, j in scored[:6]]

    return [
        JobResponse(
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
        )
        for job in jobs
    ]
