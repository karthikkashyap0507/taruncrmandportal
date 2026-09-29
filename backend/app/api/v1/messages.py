import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.message import ApplicationMessage
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.schemas.job import MessageCreate, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


def _to_response(msg: ApplicationMessage, db: Session) -> MessageResponse:
    sender = db.query(User).filter(User.id == msg.sender_id).first()
    return MessageResponse(
        id=msg.id,
        application_id=msg.application_id,
        sender_id=msg.sender_id,
        sender_name=sender.name if sender else "Unknown",
        message_type=msg.message_type,
        content=msg.content,
        created_at=msg.created_at,
    )


@router.post("/applications/{application_id}", response_model=MessageResponse, status_code=201)
def send_message(
    application_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recruiter sends message/approval/interview invite to candidate."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify recruiter owns the job OR candidate owns the application
    if user.role in (UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin):
        recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
        job = db.query(Job).filter(Job.id == app.job_id).first()
        if recruiter and job and job.recruiter_id != recruiter.id and user.role != UserRole.platform_admin:
            raise HTTPException(status_code=403, detail="Not your job")
    elif user.role == UserRole.candidate:
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if not candidate or candidate.id != app.candidate_id:
            raise HTTPException(status_code=403, detail="Not your application")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    msg = ApplicationMessage(
        application_id=application_id,
        sender_id=user.id,
        message_type=payload.message_type,
        content=payload.content,
    )
    db.add(msg)

    # Also update application status based on message type
    if payload.message_type.value == "interview_invite":
        app.status = "interview"
    elif payload.message_type.value == "offer":
        app.status = "offered"
    elif payload.message_type.value == "rejection":
        app.status = "rejected"
    elif payload.message_type.value == "approval":
        app.status = "screening"

    db.commit()
    db.refresh(msg)

    # ── Email notification to the recipient ──────────────────────────────────
    try:
        from app.services.email import send_message_notification_email
        job = db.query(Job).filter(Job.id == app.job_id).first()
        job_title = job.title if job else f"Job #{app.job_id}"

        if user.role in (UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin):
            # Recruiter → candidate
            candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
            if candidate:
                candidate_user = db.query(User).filter(User.id == candidate.user_id).first()
                if candidate_user:
                    send_message_notification_email(
                        to_email=candidate_user.email,
                        to_name=candidate_user.name,
                        sender_name=user.name,
                        job_title=job_title,
                        message_type=payload.message_type.value,
                        content=payload.content,
                    )
        elif user.role == UserRole.candidate:
            # Candidate → recruiter
            if job:
                recruiter_user = (
                    db.query(User)
                    .join(Recruiter, Recruiter.user_id == User.id)
                    .filter(Recruiter.id == job.recruiter_id)
                    .first()
                )
                if recruiter_user:
                    send_message_notification_email(
                        to_email=recruiter_user.email,
                        to_name=recruiter_user.name,
                        sender_name=user.name,
                        job_title=job_title,
                        message_type="message",
                        content=payload.content,
                    )
    except Exception as e:
        logger.error(f"Email error on message send: {e}")

    return _to_response(msg, db)


@router.get("/applications/{application_id}", response_model=list[MessageResponse])
def get_application_messages(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all messages for an application."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Auth check
    if user.role == UserRole.candidate:
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if not candidate or candidate.id != app.candidate_id:
            raise HTTPException(status_code=403, detail="Not your application")

    messages = (
        db.query(ApplicationMessage)
        .filter(ApplicationMessage.application_id == application_id)
        .order_by(ApplicationMessage.created_at.asc())
        .all()
    )
    return [_to_response(m, db) for m in messages]


@router.get("/candidate/inbox", response_model=list[dict])
def get_candidate_inbox(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All messages received by a candidate across all applications."""
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=403, detail="Candidates only")
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Profile not found")

    apps = db.query(Application).filter(Application.candidate_id == candidate.id).all()
    result = []
    for app in apps:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        messages = (
            db.query(ApplicationMessage)
            .filter(
                ApplicationMessage.application_id == app.id,
                ApplicationMessage.sender_id != user.id,  # only from recruiters
            )
            .order_by(ApplicationMessage.created_at.desc())
            .all()
        )
        for msg in messages:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            result.append({
                "id": msg.id,
                "application_id": app.id,
                "job_id": app.job_id,
                "job_title": job.title if job else f"Job #{app.job_id}",
                "sender_name": sender.name if sender else "Recruiter",
                "message_type": msg.message_type,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "status": app.status,
            })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result
