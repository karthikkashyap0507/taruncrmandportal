import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.application import Application, ApplicationStatus
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.schemas.job import ApplicationCreate, ApplicationResponse, ApplicationUpdate, CandidateInfo, CompanyResponse, JobCreate, JobResponse, JobUpdate

router = APIRouter(prefix="/jobs", tags=["jobs"])

# ─────────────────────────────────────────────
# ATS Score Computation
# ─────────────────────────────────────────────

_STOP_WORDS = {
    "that","this","with","from","have","been","will","they","your","their",
    "which","about","would","there","other","these","those","should","could",
    "after","before","where","while","since","under","through","between",
    "during","including","within","without","having","looking","working",
    "required","experience","candidate","skills","ability","strong","using",
    "years","work","team","good","also","must","need","able","well",
    "plus","role","join","help","make","build","want","like","more",
    "great","excellent","seeking","hire","position","opportunity",
    "responsibilities","qualifications","minimum","preferred","knowledge",
    "understanding","proficiency",
}


def _compute_ats(job: Job, app: Application, candidate) -> dict:
    """Compute ATS match score 0-100 with breakdown."""

    # ── 1. Skills Match (60 pts) ──────────────────────────
    job_skills  = [s.lower().strip() for s in (job.skills or [])]
    cand_skills = [s.lower().strip() for s in (getattr(candidate, "skills", None) or [])]

    matched_skills: list = []
    if job_skills:
        for js in job_skills:
            for cs in cand_skills:
                if js == cs or js in cs or cs in js:
                    matched_skills.append(js)
                    break
        skills_score = round((len(matched_skills) / len(job_skills)) * 60)
    else:
        skills_score = 30   # neutral

    # ── 2. Experience Match (20 pts) ─────────────────────
    exp_level = (job.experience_level or "").lower()
    years     = app.years_experience or 0

    if not exp_level:
        exp_score = 10
    elif any(k in exp_level for k in ["entry","junior","fresher","intern","0-1","0-2"]):
        exp_score = 20 if years <= 2 else (12 if years <= 4 else 4)
    elif any(k in exp_level for k in ["mid","2-5","3-5","2-4","associate","intermediate"]):
        exp_score = 20 if 2 <= years <= 5 else (8 if years < 2 else 14)
    elif any(k in exp_level for k in ["senior","lead","principal","staff","5+","5-10","7+"]):
        exp_score = 20 if years >= 5 else (10 if years >= 3 else 4)
    else:
        nums = re.findall(r"\d+", exp_level)
        if nums:
            required  = int(nums[0])
            exp_score = 20 if years >= required else max(0, int((years / max(required, 1)) * 20))
        else:
            exp_score = 10

    # ── 3. Keyword Match (20 pts) ─────────────────────────
    job_text  = f"{job.title} {job.description}".lower()
    cover     = (app.cover_letter or "").lower()
    headline  = (getattr(candidate, "headline", None) or "").lower()
    cand_text = f"{cover} {headline} {' '.join(cand_skills)}"

    raw_words = re.findall(r"\b[a-z]{4,}\b", job_text)
    keywords  = list(dict.fromkeys([w for w in raw_words if w not in _STOP_WORDS]))[:40]
    if keywords:
        matched_kw = [k for k in keywords if k in cand_text]
        kw_score   = round((len(matched_kw) / len(keywords)) * 20)
    else:
        matched_kw = []
        kw_score   = 10

    total = min(skills_score + exp_score + kw_score, 100)
    return {
        "total":            total,
        "skills_score":     skills_score,
        "exp_score":        exp_score,
        "kw_score":         kw_score,
        "matched_skills":   matched_skills,
        "total_job_skills": len(job_skills),
        "matched_keywords": len(matched_kw) if keywords else 0,
        "total_keywords":   len(keywords),
        "candidate_years":  years,
        "required_exp":     job.experience_level or "Not specified",
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def job_to_response(job: Job) -> JobResponse:
    return JobResponse(
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


def _build_app_response(app: Application, db: Session) -> ApplicationResponse:
    candidate_info = None
    cand = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
    if cand:
        cand_user = db.query(User).filter(User.id == cand.user_id).first()
        if cand_user:
            candidate_info = CandidateInfo(
                user_id=cand_user.id,
                name=cand_user.name,
                email=cand_user.email,
                headline=cand.headline,
                skills=cand.skills or [],
                resume_url=app.resume_url or cand.resume_url,
            )
    return ApplicationResponse(
        id=app.id,
        candidate_id=app.candidate_id,
        job_id=app.job_id,
        status=app.status,
        score=app.score,
        applied_at=app.applied_at,
        full_name=app.full_name or (candidate_info.name if candidate_info else None),
        phone=app.phone,
        years_experience=app.years_experience,
        cover_letter=app.cover_letter,
        resume_url=app.resume_url or (candidate_info.resume_url if candidate_info else None),
        candidate_info=candidate_info,
    )


# ─────────────────────────────────────────────
# Routes (static paths before parameterised)
# ─────────────────────────────────────────────

@router.get("", response_model=list[JobResponse])
def list_jobs(
    q: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    employment_type: str | None = None,
    experience_level: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    skills: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Job).options(joinedload(Job.company)).filter(Job.status == JobStatus.published)
    if q:
        query = query.filter(
            Job.title.ilike(f"%{q}%") |
            Job.description.ilike(f"%{q}%") |
            Job.location.ilike(f"%{q}%")
        )
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if remote:
        query = query.filter(Job.location.ilike("%remote%"))
    if employment_type:
        query = query.filter(Job.employment_type.ilike(f"%{employment_type}%"))
    if experience_level and experience_level != "all":
        query = query.filter(Job.experience_level.ilike(f"%{experience_level}%"))
    if salary_min is not None:
        query = query.filter((Job.salary_min >= salary_min) | (Job.salary_min.is_(None)))
    if salary_max is not None:
        query = query.filter((Job.salary_max <= salary_max) | (Job.salary_max.is_(None)))
    if skills:
        # Comma-separated; each skill must appear in the job's skills JSON,
        # title or description. Cast JSON to text for a portable substring match.
        skills_text = cast(Job.skills, String)
        for term in (s.strip() for s in skills.split(",") if s.strip()):
            like = f"%{term}%"
            query = query.filter(
                skills_text.ilike(like)
                | Job.title.ilike(like)
                | Job.description.ilike(like)
            )
    jobs = query.order_by(Job.id.desc()).offset(skip).limit(limit).all()
    return [job_to_response(j) for j in jobs]


@router.get("/recruiter/my", response_model=list[JobResponse])
def list_my_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    jobs = db.query(Job).options(joinedload(Job.company)).filter(Job.recruiter_id == recruiter.id).all()
    return [job_to_response(j) for j in jobs]


@router.get("/recruiter/company", response_model=CompanyResponse)
def get_my_company(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    company = db.query(Company).filter(Company.id == recruiter.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyResponse.model_validate(company)


@router.get("/candidate/my-applications", response_model=list[ApplicationResponse])
def list_my_applications(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.candidate)),
):
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    applications = db.query(Application).filter(Application.candidate_id == candidate.id).all()
    return [ApplicationResponse.model_validate(app) for app in applications]


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    app = db.query(Application).join(Job).filter(
        Application.id == application_id, Job.recruiter_id == recruiter.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    old_status = app.status
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, key, value)
    db.commit()
    db.refresh(app)
    if payload.status and payload.status != old_status:
        try:
            from app.services.email import send_status_update_email
            candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
            if candidate:
                candidate_user = db.query(User).filter(User.id == candidate.user_id).first()
                job = db.query(Job).options(joinedload(Job.company)).filter(Job.id == app.job_id).first()
                if candidate_user and job:
                    company_name = job.company.name if job.company else ""
                    send_status_update_email(
                        candidate_user.email, candidate_user.name,
                        job.title, str(payload.status.value), company_name
                    )
        except Exception as e:
            logger.error(f"Email error on status update: {e}")
    return ApplicationResponse.model_validate(app)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).options(joinedload(Job.company)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_response(job)


@router.post("", response_model=JobResponse, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = Job(
        title=payload.title,
        description=payload.description,
        company_id=recruiter.company_id,
        recruiter_id=recruiter.id,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        skills=payload.skills,
        experience_level=payload.experience_level,
        location=payload.location,
        employment_type=payload.employment_type,
        status=payload.status,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.refresh(job, ["company"])
    return job_to_response(job)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = db.query(Job).options(joinedload(Job.company)).filter(
        Job.id == job_id, Job.recruiter_id == recruiter.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job_to_response(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == recruiter.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Remove saved-job references (no ORM relationship for cascade), then delete the
    # job — applications and their messages cascade via the ORM relationship.
    from app.models.saved_job import SavedJob
    db.query(SavedJob).filter(SavedJob.job_id == job_id).delete(synchronize_session=False)
    try:
        db.delete(job)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=409, detail="Unable to delete job")


@router.post("/{job_id}/apply")
def apply_job(
    job_id: int,
    payload: ApplicationCreate = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.candidate)),
):
    job = db.query(Job).options(joinedload(Job.company)).filter(
        Job.id == job_id, Job.status == JobStatus.published
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    existing = db.query(Application).filter(
        Application.candidate_id == candidate.id, Application.job_id == job_id
    ).first()
    if existing:
        return {"message": "Already applied", "job_id": job_id, "application_id": existing.id, "already_applied": True}

    app = Application(
        candidate_id=candidate.id,
        job_id=job_id,
        status=ApplicationStatus.applied,
        full_name=(payload.full_name if payload else None) or user.name,
        phone=payload.phone if payload else None,
        years_experience=payload.years_experience if payload else None,
        cover_letter=payload.cover_letter if payload else None,
        resume_url=(payload.resume_url if payload else None) or candidate.resume_url,
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # Auto-compute ATS score immediately on apply
    try:
        result = _compute_ats(job, app, candidate)
        app.score = float(result["total"])
        db.commit()
    except Exception:
        pass

    try:
        from app.services.email import send_application_received_email, send_recruiter_new_application_email
        company_name = job.company.name if job.company else "the company"
        # Email candidate
        send_application_received_email(user.email, user.name, job.title, company_name)
        # Email recruiter
        recruiter_user = db.query(User).join(Recruiter, Recruiter.user_id == User.id).filter(
            Recruiter.id == job.recruiter_id
        ).first()
        if recruiter_user:
            send_recruiter_new_application_email(
                to_email=recruiter_user.email,
                recruiter_name=recruiter_user.name,
                candidate_name=user.name,
                job_title=job.title,
                candidate_email=user.email,
                years_exp=app.years_experience,
            )
    except Exception as e:
        logger.error(f"Email error on apply: {e}")
    return {"message": "Application submitted", "job_id": job_id, "application_id": app.id, "already_applied": False}


@router.get("/{job_id}/applications", response_model=list[ApplicationResponse])
def list_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == recruiter.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    return [_build_app_response(app, db) for app in applications]


# ─────────────────────────────────────────────
# ATS Endpoints
# ─────────────────────────────────────────────

@router.post("/{job_id}/applications/{application_id}/compute-ats")
def compute_ats_single(
    job_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    """Compute and save ATS score for one application."""
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == recruiter.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    app = db.query(Application).filter(
        Application.id == application_id, Application.job_id == job_id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
    result = _compute_ats(job, app, candidate)
    app.score = float(result["total"])
    db.commit()
    return {"application_id": application_id, **result}


@router.post("/{job_id}/compute-ats-all")
def compute_ats_all(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)),
):
    """Compute and save ATS scores for all applications on a job."""
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == recruiter.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    results = []
    for app in applications:
        candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
        r = _compute_ats(job, app, candidate)
        app.score = float(r["total"])
        results.append({"application_id": app.id, **r})
    db.commit()
    return {"computed": len(results), "results": results}
