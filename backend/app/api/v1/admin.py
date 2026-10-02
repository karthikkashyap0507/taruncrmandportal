import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.application import Application
from app.models.audit import AuditLog
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.enquiry import ContactMessage, NewsletterSubscriber
from app.models.job import Job, JobStatus
from app.models.outbox import EmailOutbox
from app.models.recruiter import Recruiter
from app.models.saved_job import SavedJob
from app.models.session import UserSession
from app.models.user import User, UserRole
from app.services import newsletter, outbox
from app.services.audit import audit

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = require_roles(UserRole.platform_admin)


class UserAdminResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    is_active: bool = True
    locked_until: Optional[datetime] = None
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
    pending_jobs: int = 0
    premium_jobs: int = 0
    failed_emails: int = 0
    new_enquiries: int = 0
    newsletter_subscribers: int = 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db), _: User = Depends(AdminUser)):
    return AdminStats(
        total_users=db.query(User).count(),
        total_candidates=db.query(Candidate).count(),
        total_recruiters=db.query(Recruiter).count(),
        total_companies=db.query(Company).count(),
        total_jobs=db.query(Job).count(),
        published_jobs=db.query(Job).filter(Job.status == JobStatus.published).count(),
        total_applications=db.query(Application).count(),
        pending_jobs=db.query(Job).filter(Job.status == JobStatus.pending).count(),
        premium_jobs=db.query(Job).filter(Job.is_premium.is_(True), Job.status == JobStatus.published).count(),
        failed_emails=db.query(EmailOutbox).filter(EmailOutbox.status.in_(["failed", "dead"])).count(),
        new_enquiries=db.query(ContactMessage).filter(ContactMessage.status == "new").count(),
        newsletter_subscribers=db.query(NewsletterSubscriber).filter(
            NewsletterSubscriber.confirmed_at.isnot(None), NewsletterSubscriber.unsubscribed_at.is_(None)).count(),
    )


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if not include_inactive:
        q = q.filter(User.is_active.isnot(False))
    return q.order_by(User.id.desc()).offset(skip).limit(limit).all()


def _deactivate(db: Session, user: User) -> None:
    """Soft-delete: block sign-in, end every session, take the user's jobs offline.
    History (applications, audit trail) is kept."""
    user.is_active = False
    db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)) \
        .update({UserSession.revoked_at: _now()}, synchronize_session=False)
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if recruiter:
        db.query(Job).filter(Job.recruiter_id == recruiter.id, Job.status == JobStatus.published) \
            .update({Job.status: JobStatus.closed}, synchronize_session=False)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email.endswith("@jobsnexgen.system"):
        raise HTTPException(status_code=400, detail="This is the system account the CRM publishes client jobs "
                                                    "under; close jobs from the CRM instead")
    _deactivate(db, user)
    audit(db, "admin.user_deactivated", actor=admin, entity_type="user", entity_id=user.id,
          details={"email": user.email, "role": user.role.value}, request=request)
    db.commit()


@router.post("/users/{user_id}/activate")
def activate_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active, user.failed_login_count, user.locked_until = True, 0, None
    audit(db, "admin.user_activated", actor=admin, entity_type="user", entity_id=user.id, request=request)
    db.commit()
    return {"message": "User activated"}


@router.post("/users/{user_id}/unlock")
def unlock_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.failed_login_count, user.locked_until = 0, None
    audit(db, "admin.user_unlocked", actor=admin, entity_type="user", entity_id=user.id, request=request)
    db.commit()
    return {"message": "Account unlocked"}


@router.get("/companies", response_model=list[CompanyAdminResponse])
def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    counts = dict(db.query(Job.company_id, func.count(Job.id)).group_by(Job.company_id).all())
    companies = db.query(Company).order_by(Company.id.desc()).offset(skip).limit(limit).all()
    return [CompanyAdminResponse(id=c.id, name=c.name, website=c.website, industry=c.industry,
                                 job_count=counts.get(c.id, 0)) for c in companies]


@router.delete("/companies/{company_id}", status_code=204)
def delete_company(company_id: int, request: Request, db: Session = Depends(get_db),
                   admin: User = Depends(AdminUser)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    # Deactivate the company's recruiters, then remove its jobs (applications and
    # messages cascade) and finally the company itself.
    recruiters = db.query(Recruiter).filter(Recruiter.company_id == company_id).all()
    for r in recruiters:
        u = db.get(User, r.user_id)
        if u:
            _deactivate(db, u)
    jobs = db.query(Job).filter(Job.company_id == company_id).all()
    job_ids = [j.id for j in jobs]
    if job_ids:
        db.query(SavedJob).filter(SavedJob.job_id.in_(job_ids)).delete(synchronize_session=False)
    for j in jobs:
        db.delete(j)
    db.flush()
    for r in recruiters:
        db.delete(r)
    db.flush()
    audit(db, "admin.company_deleted", actor=admin, entity_type="company", entity_id=company_id,
          details={"name": company.name, "jobs_removed": len(job_ids), "recruiters_deactivated": len(recruiters)},
          request=request)
    db.delete(company)
    db.commit()


@router.get("/jobs")
def list_all_jobs(
    status: Optional[JobStatus] = None,
    plan: Optional[str] = Query(None, description="premium | free"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    q = db.query(Job).options(joinedload(Job.company), joinedload(Job.recruiter).joinedload(Recruiter.user))
    if status:
        q = q.filter(Job.status == status)
    if plan in ("premium", "free"):
        q = q.filter(Job.is_premium.is_(plan == "premium"))
    jobs = q.order_by(Job.id.desc()).offset(skip).limit(limit).all()
    return [{
        "id": j.id, "title": j.title, "status": j.status, "company_id": j.company_id,
        "company_name": j.company.name if j.company else None,
        "posted_by": j.recruiter.user.name if j.recruiter and j.recruiter.user else None,
        "posted_by_email": j.recruiter.user.email if j.recruiter and j.recruiter.user else None,
        "location": j.location, "locality": j.locality, "education": j.education,
        "salary_min": j.salary_min, "salary_max": j.salary_max,
        "salary_period": j.salary_period or ("year" if (j.salary_min or j.salary_max) else None),
        "employment_type": j.employment_type, "experience_level": j.experience_level,
        "description": j.description, "review_note": j.review_note, "created_at": j.created_at,
        "is_premium": bool(j.is_premium), "source": j.source or "portal", "expires_at": j.expires_at,
    } for j in jobs]


class PremiumBody(BaseModel):
    is_premium: bool


@router.post("/jobs/{job_id}/premium")
def set_job_plan(job_id: int, body: PremiumBody, request: Request, db: Session = Depends(get_db),
                 admin: User = Depends(AdminUser)):
    """Premium jobs are ones a client pays for; only they are sent to the CRM for the HR team."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.source == "crm" and not body.is_premium:
        raise HTTPException(status_code=409, detail="Jobs published from the CRM are client jobs and stay premium")
    job.is_premium = body.is_premium
    audit(db, "admin.job_plan_changed", actor=admin, entity_type="job", entity_id=job.id,
          details={"title": job.title, "plan": "premium" if body.is_premium else "free"}, request=request)
    db.commit()
    return {"id": job.id, "is_premium": job.is_premium}


def _review(db: Session, job_id: int, approve: bool, note: Optional[str], admin: User, request: Request) -> dict:
    job = db.query(Job).options(joinedload(Job.recruiter).joinedload(Recruiter.user)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if approve:
        job.status, job.review_note = JobStatus.published, None
        job.approved_at, job.approved_by_id = _now(), admin.id
    else:
        job.status, job.review_note = JobStatus.rejected, note
    audit(db, "admin.job_approved" if approve else "admin.job_rejected", actor=admin, entity_type="job",
          entity_id=job.id, details={"title": job.title, "reason": note} if not approve else {"title": job.title},
          request=request)
    db.commit()
    poster = job.recruiter.user if job.recruiter else None
    if poster:
        from app.services.email import send_job_review_email
        send_job_review_email(poster.email, poster.name, job.id, job.title, approve, note)
    return {"id": job.id, "status": job.status.value, "review_note": job.review_note}


class RejectJobBody(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


@router.post("/jobs/{job_id}/approve")
def approve_job(job_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    """Publish an employer's job; the poster is emailed."""
    return _review(db, job_id, True, None, admin, request)


@router.post("/jobs/{job_id}/reject")
def reject_job(job_id: int, body: RejectJobBody, request: Request, db: Session = Depends(get_db),
               admin: User = Depends(AdminUser)):
    """Turn down an employer's job with a reason the poster sees; they can edit and resubmit."""
    return _review(db, job_id, False, body.reason.strip(), admin, request)


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: int,
    status: JobStatus,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(AdminUser),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    old = job.status
    job.status = status
    if status == JobStatus.published and not job.approved_at:
        job.approved_at, job.approved_by_id = _now(), admin.id
    audit(db, "admin.job_status_changed", actor=admin, entity_type="job", entity_id=job.id,
          details={"from": old.value, "to": status.value}, request=request)
    db.commit()
    return {"message": "Status updated", "job_id": job_id, "status": status}


# ── Audit trail ───────────────────────────────────────────────────────────────

@router.get("/audit-logs")
def list_audit_logs(
    action: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.like(f"{action}%"))
    if actor_user_id:
        q = q.filter(AuditLog.actor_user_id == actor_user_id)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    total = q.count()
    rows = q.order_by(AuditLog.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "data": [{
        "id": r.id, "created_at": r.created_at, "action": r.action,
        "actor_user_id": r.actor_user_id, "actor_email": r.actor_email,
        "entity_type": r.entity_type, "entity_id": r.entity_id,
        "details": r.details, "ip_address": r.ip_address,
    } for r in rows]}


# ── Email delivery log ────────────────────────────────────────────────────────

@router.get("/notifications")
def list_email_deliveries(
    status: Optional[str] = Query(None, description="pending | sent | failed | dead"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    q = db.query(EmailOutbox)
    if status:
        q = q.filter(EmailOutbox.status == status)
    total = q.count()
    rows = q.order_by(EmailOutbox.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "data": [{
        "id": r.id, "category": r.category, "to_email": r.to_email, "subject": r.subject,
        "status": r.status, "attempts": r.attempts, "last_error": r.last_error,
        "next_attempt_at": r.next_attempt_at, "created_at": r.created_at, "sent_at": r.sent_at,
    } for r in rows]}


@router.post("/notifications/{outbox_id}/retry")
def retry_email(outbox_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    row = db.get(EmailOutbox, outbox_id)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row.status == "sent":
        return {"message": "Already sent", "status": "sent"}
    audit(db, "admin.email_retried", actor=admin, entity_type="email", entity_id=outbox_id, request=request)
    db.commit()
    ok = outbox.deliver(outbox_id, force=True)
    db.refresh(row)
    return {"message": "Sent" if ok else "Still failing", "status": row.status, "last_error": row.last_error}


@router.post("/notifications/retry-failed")
def retry_all_failed(request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    ids = [r.id for r in db.query(EmailOutbox.id).filter(EmailOutbox.status.in_(["failed", "dead"])).limit(200)]
    audit(db, "admin.email_retry_all", actor=admin, details={"count": len(ids)}, request=request)
    db.commit()
    sent = sum(1 for i in ids if outbox.deliver(i, force=True))
    return {"attempted": len(ids), "sent": sent, "still_failing": len(ids) - sent}


# ── Contact-form enquiries ────────────────────────────────────────────────────

@router.get("/enquiries")
def list_enquiries(
    status: Optional[str] = Query(None, description="new | handled"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    q = db.query(ContactMessage)
    if status:
        q = q.filter(ContactMessage.status == status)
    total = q.count()
    rows = q.order_by(ContactMessage.id.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "new": db.query(ContactMessage).filter(ContactMessage.status == "new").count(),
        "data": [{
            "id": r.id, "name": r.name, "email": r.email, "subject": r.subject, "message": r.message,
            "status": r.status, "created_at": r.created_at, "handled_at": r.handled_at,
        } for r in rows],
    }


def _set_enquiry_status(db: Session, enquiry_id: int, status: str, admin: User, request: Request) -> dict:
    row = db.get(ContactMessage, enquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    row.status = status
    row.handled_by_id = admin.id if status == "handled" else None
    row.handled_at = _now() if status == "handled" else None
    audit(db, f"admin.enquiry_{status}", actor=admin, entity_type="enquiry", entity_id=enquiry_id, request=request)
    db.commit()
    return {"id": row.id, "status": row.status}


@router.post("/enquiries/{enquiry_id}/handled")
def mark_enquiry_handled(enquiry_id: int, request: Request, db: Session = Depends(get_db),
                         admin: User = Depends(AdminUser)):
    return _set_enquiry_status(db, enquiry_id, "handled", admin, request)


@router.post("/enquiries/{enquiry_id}/reopen")
def reopen_enquiry(enquiry_id: int, request: Request, db: Session = Depends(get_db),
                   admin: User = Depends(AdminUser)):
    return _set_enquiry_status(db, enquiry_id, "new", admin, request)


# ── Newsletter ────────────────────────────────────────────────────────────────

@router.get("/newsletter")
def list_subscribers(
    status: Optional[str] = Query(None, description="confirmed | pending | unsubscribed"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(AdminUser),
):
    S = NewsletterSubscriber
    filters = {
        "confirmed": (S.confirmed_at.isnot(None), S.unsubscribed_at.is_(None)),
        "pending": (S.confirmed_at.is_(None), S.unsubscribed_at.is_(None)),
        "unsubscribed": (S.unsubscribed_at.isnot(None),),
    }
    if status and status not in filters:
        raise HTTPException(status_code=422, detail="status must be confirmed, pending or unsubscribed")
    counts = {name: db.query(S).filter(*conds).count() for name, conds in filters.items()}
    q = db.query(S).filter(*filters[status]) if status else db.query(S)
    total = q.count()
    rows = q.order_by(S.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "counts": counts, "data": [{
        "id": r.id, "email": r.email, "created_at": r.created_at, "confirmed_at": r.confirmed_at,
        "unsubscribed_at": r.unsubscribed_at, "last_digest_at": r.last_digest_at,
    } for r in rows]}


@router.post("/newsletter/send-digest")
def send_digest_now(request: Request, db: Session = Depends(get_db), admin: User = Depends(AdminUser)):
    """Send this week's job alert now instead of waiting for Monday 09:00 IST."""
    ids, job_count = newsletter.queue_digest(force=True)
    audit(db, "admin.newsletter_sent", actor=admin, details={"recipients": len(ids), "jobs": job_count},
          request=request)
    db.commit()
    if not job_count:
        return {"queued": 0, "message": "No new jobs were posted in the last 7 days, so there is nothing to send."}
    if not ids:
        return {"queued": 0, "message": "Every confirmed subscriber has already had a job alert in the last 6 days."}
    threading.Thread(target=newsletter.deliver_slowly, args=(ids,), daemon=True).start()
    return {"queued": len(ids), "message": f"Sending {job_count} new job(s) to {len(ids)} subscriber(s)."}
