import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import get_current_user, get_optional_user, require_roles
from app.core.database import get_db
from app.core.files import own_resume_ref, sign_resume_url
from app.models.application import Application, ApplicationStatus
from app.models.application_event import ApplicationEvent
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.recruiter import Recruiter
from app.models.saved_job import SavedJob
from app.models.user import User, UserRole
from app.schemas.job import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    CandidateInfo,
    CompanyResponse,
    JobCreate,
    JobResponse,
    JobUpdate,
)
from app.services import ats
from app.services.audit import audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])

EMPLOYER_ROLES = (UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)

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


def _build_app_response(app: Application) -> ApplicationResponse:
    """Application as seen by an authorised viewer. Expects candidate + user preloaded.
    Resume links are signed and expire, so they can't be shared onwards."""
    candidate_info = None
    cand = app.candidate
    if cand and cand.user:
        candidate_info = CandidateInfo(
            user_id=cand.user.id,
            name=cand.user.name,
            email=cand.user.email,
            headline=cand.headline,
            skills=cand.skills or [],
            resume_url=sign_resume_url(app.resume_url or cand.resume_url),
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
        resume_url=sign_resume_url(app.resume_url or (cand.resume_url if cand else None)),
        candidate_info=candidate_info,
    )


def _recruiter_for(db: Session, user: User) -> Recruiter | None:
    return db.query(Recruiter).filter(Recruiter.user_id == user.id).first()


def _can_manage(user: User, recruiter: Recruiter | None, job: Job) -> bool:
    """Recruiters manage their own jobs; company admins manage their company's jobs;
    platform admins manage everything."""
    if user.role == UserRole.platform_admin:
        return True
    if not recruiter:
        return False
    if job.recruiter_id == recruiter.id:
        return True
    return user.role == UserRole.company_admin and job.company_id == recruiter.company_id


def _manageable_job(db: Session, user: User, job_id: int, with_company: bool = False) -> Job:
    q = db.query(Job)
    if with_company:
        q = q.options(joinedload(Job.company))
    job = q.filter(Job.id == job_id).first()
    if not job or not _can_manage(user, _recruiter_for(db, user), job):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _notify_status(db: Session, app: Application, new_status: str) -> None:
    try:
        from app.services.email import send_status_update_email
        cand = db.query(Candidate).options(joinedload(Candidate.user)).filter(Candidate.id == app.candidate_id).first()
        job = db.query(Job).options(joinedload(Job.company)).filter(Job.id == app.job_id).first()
        if cand and cand.user and job:
            send_status_update_email(cand.user.email, cand.user.name, job.title, new_status,
                                     job.company.name if job.company else "")
    except Exception:
        logger.exception("status email failed")


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
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    recruiter = _recruiter_for(db, user)
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    q = db.query(Job).options(joinedload(Job.company))
    if user.role == UserRole.company_admin:
        q = q.filter(Job.company_id == recruiter.company_id)
    else:
        q = q.filter(Job.recruiter_id == recruiter.id)
    jobs = q.order_by(Job.id.desc()).offset(skip).limit(limit).all()
    return [job_to_response(j) for j in jobs]


@router.get("/recruiter/company", response_model=CompanyResponse)
def get_my_company(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    recruiter = _recruiter_for(db, user)
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
    applications = (db.query(Application).filter(Application.candidate_id == candidate.id)
                    .order_by(Application.id.desc()).all())
    out = []
    for app in applications:
        item = ApplicationResponse.model_validate(app)
        item.resume_url = sign_resume_url(app.resume_url)
        out.append(item)
    return out


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    app = (db.query(Application)
           .options(joinedload(Application.candidate).joinedload(Candidate.user), joinedload(Application.job))
           .filter(Application.id == application_id).first())
    if not app or not _can_manage(user, _recruiter_for(db, user), app.job):
        raise HTTPException(status_code=404, detail="Application not found")
    if payload.status is None:
        return _build_app_response(app)

    old = ats.change_status(db, app, payload.status, user.id, note=payload.note)
    audit(db, "application.status_changed", actor=user, entity_type="application", entity_id=app.id,
          details={"from": old.value, "to": payload.status.value, "note": payload.note}, request=request)
    db.commit()
    db.refresh(app)
    _notify_status(db, app, payload.status.value)
    return _build_app_response(app)


@router.post("/applications/{application_id}/withdraw", response_model=ApplicationResponse)
def withdraw_application(
    application_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.candidate)),
):
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app or not candidate or app.candidate_id != candidate.id:
        raise HTTPException(status_code=404, detail="Application not found")
    old = ats.change_status(db, app, ApplicationStatus.withdrawn, user.id, by_candidate=True)
    audit(db, "application.withdrawn", actor=user, entity_type="application", entity_id=app.id,
          details={"from": old.value}, request=request)
    db.commit()
    try:
        from app.services.email import send_message_notification_email
        job = db.get(Job, app.job_id)
        recruiter_user = (db.query(User).join(Recruiter, Recruiter.user_id == User.id)
                          .filter(Recruiter.id == job.recruiter_id).first()) if job else None
        if recruiter_user:
            send_message_notification_email(recruiter_user.email, recruiter_user.name, user.name, job.title,
                                            "message", f"{user.name} has withdrawn their application.")
    except Exception:
        logger.exception("withdraw email failed")
    item = ApplicationResponse.model_validate(app)
    item.resume_url = sign_resume_url(app.resume_url)
    return item


@router.get("/applications/{application_id}/history")
def application_history(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """ATS history of one application, for its candidate or the managing recruiters."""
    app = (db.query(Application).options(joinedload(Application.job), joinedload(Application.candidate))
           .filter(Application.id == application_id).first())
    allowed = bool(app) and (
        (user.role == UserRole.candidate and app.candidate and app.candidate.user_id == user.id)
        or (user.role in EMPLOYER_ROLES and _can_manage(user, _recruiter_for(db, user), app.job))
    )
    if not allowed:
        raise HTTPException(status_code=404, detail="Application not found")
    events = (db.query(ApplicationEvent).filter(ApplicationEvent.application_id == application_id)
              .order_by(ApplicationEvent.id).all())
    return [{"from_status": e.from_status, "to_status": e.to_status, "note": e.note,
             "actor_user_id": e.actor_user_id, "created_at": e.created_at} for e in events]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    job = db.query(Job).options(joinedload(Job.company)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Drafts and closed jobs are only visible to the people who manage them
    if job.status != JobStatus.published and not (user and user.role in EMPLOYER_ROLES
                                                  and _can_manage(user, _recruiter_for(db, user), job)):
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_response(job)


@router.post("", response_model=JobResponse, status_code=201)
def create_job(
    payload: JobCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    recruiter = _recruiter_for(db, user)
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    job = Job(
        title=payload.title.strip(),
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
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    audit(db, "job.created", actor=user, entity_type="job", entity_id=job.id,
          details={"title": job.title, "status": job.status.value}, request=request)
    db.commit()
    db.refresh(job)
    db.refresh(job, ["company"])
    return job_to_response(job)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    payload: JobUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    job = _manageable_job(db, user, job_id, with_company=True)
    changes = payload.model_dump(exclude_unset=True)
    _min = changes.get("salary_min", job.salary_min)
    _max = changes.get("salary_max", job.salary_max)
    if _min is not None and _max is not None and _min > _max:
        raise HTTPException(status_code=422, detail="Minimum salary cannot be greater than maximum salary")
    before = {k: getattr(job, k) for k in changes}
    for key, value in changes.items():
        setattr(job, key, value)
    audit(db, "job.updated", actor=user, entity_type="job", entity_id=job.id,
          details={"before": {k: (v.value if hasattr(v, "value") else v) for k, v in before.items()},
                   "after": {k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()}},
          request=request)
    db.commit()
    db.refresh(job)
    return job_to_response(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    job = _manageable_job(db, user, job_id)
    # Remove saved-job references (no ORM relationship for cascade), then delete the
    # job — applications and their messages cascade via the ORM relationship.
    db.query(SavedJob).filter(SavedJob.job_id == job_id).delete(synchronize_session=False)
    audit(db, "job.deleted", actor=user, entity_type="job", entity_id=job.id,
          details={"title": job.title}, request=request)
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
    request: Request,
    payload: ApplicationCreate | None = None,
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

    resume_ref = own_resume_ref(payload.resume_url if payload else None, user.id) or candidate.resume_url
    app = Application(
        candidate_id=candidate.id,
        job_id=job_id,
        status=ApplicationStatus.applied,
        full_name=(payload.full_name if payload else None) or user.name,
        phone=payload.phone if payload else None,
        years_experience=payload.years_experience if payload else None,
        cover_letter=payload.cover_letter if payload else None,
        resume_url=resume_ref,
    )
    db.add(app)
    try:
        db.flush()
    except IntegrityError:
        # A second, simultaneous click: the unique index stopped the duplicate
        db.rollback()
        existing = db.query(Application).filter(
            Application.candidate_id == candidate.id, Application.job_id == job_id).first()
        return {"message": "Already applied", "job_id": job_id,
                "application_id": existing.id if existing else None, "already_applied": True}

    ats.record_applied(db, app, user.id)
    try:
        app.score = float(_compute_ats(job, app, candidate)["total"])
    except Exception:
        logger.exception("ATS scoring failed")
    audit(db, "application.created", actor=user, entity_type="application", entity_id=app.id,
          details={"job_id": job_id}, request=request)
    db.commit()

    try:
        from app.services.email import send_application_received_email, send_recruiter_new_application_email
        company_name = job.company.name if job.company else "the company"
        send_application_received_email(user.email, user.name, job.title, company_name)
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
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    _manageable_job(db, user, job_id)
    applications = (
        db.query(Application)
        .options(joinedload(Application.candidate).joinedload(Candidate.user))
        .filter(Application.job_id == job_id)
        .order_by(Application.id.desc())
        .offset(skip).limit(limit).all()
    )
    return [_build_app_response(app) for app in applications]


# ─────────────────────────────────────────────
# ATS Endpoints
# ─────────────────────────────────────────────

@router.post("/{job_id}/applications/{application_id}/compute-ats")
def compute_ats_single(
    job_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    """Compute and save ATS score for one application."""
    job = _manageable_job(db, user, job_id)
    app = (db.query(Application).options(joinedload(Application.candidate))
           .filter(Application.id == application_id, Application.job_id == job_id).first())
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    result = _compute_ats(job, app, app.candidate)
    app.score = float(result["total"])
    db.commit()
    return {"application_id": application_id, **result}


@router.post("/{job_id}/compute-ats-all")
def compute_ats_all(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EMPLOYER_ROLES)),
):
    """Compute and save ATS scores for all applications on a job."""
    job = _manageable_job(db, user, job_id)
    applications = (db.query(Application).options(joinedload(Application.candidate))
                    .filter(Application.job_id == job_id).all())
    results = []
    for app in applications:
        r = _compute_ats(job, app, app.candidate)
        app.score = float(r["total"])
        results.append({"application_id": app.id, **r})
    db.commit()
    return {"computed": len(results), "results": results}
