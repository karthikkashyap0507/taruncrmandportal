import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.application import Application, ApplicationStatus
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.message import ApplicationMessage, MessageType
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.schemas.job import MessageCreate, MessageResponse
from app.services import ats
from app.services.audit import audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])

EMPLOYER_ROLES = (UserRole.recruiter, UserRole.company_admin, UserRole.platform_admin)

# Recruiter message types that also move the application along the ATS pipeline
_STATUS_FOR_TYPE = {
    MessageType.approval: ApplicationStatus.screening,
    MessageType.interview_invite: ApplicationStatus.interview,
    MessageType.offer: ApplicationStatus.offered,
    MessageType.rejection: ApplicationStatus.rejected,
}


def _to_response(msg: ApplicationMessage) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        application_id=msg.application_id,
        sender_id=msg.sender_id,
        sender_name=msg.sender.name if msg.sender else "Unknown",
        message_type=msg.message_type,
        content=msg.content,
        created_at=msg.created_at,
    )


def _authorised_application(db: Session, user: User, application_id: int) -> Application:
    """The application if this user may see its conversation, otherwise 404.
    Candidates: their own applications. Recruiters: jobs they manage (own job, or
    any job of their company for company admins). Platform admins: all."""
    app = (db.query(Application)
           .options(joinedload(Application.job), joinedload(Application.candidate))
           .filter(Application.id == application_id).first())
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if user.role == UserRole.candidate:
        if app.candidate and app.candidate.user_id == user.id:
            return app
    elif user.role == UserRole.platform_admin:
        return app
    elif user.role in EMPLOYER_ROLES:
        recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
        job = app.job
        if recruiter and job and (job.recruiter_id == recruiter.id or
                                  (user.role == UserRole.company_admin and job.company_id == recruiter.company_id)):
            return app
    raise HTTPException(status_code=404, detail="Application not found")


@router.post("/applications/{application_id}", response_model=MessageResponse, status_code=201)
def send_message(
    application_id: int,
    payload: MessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a message on an application thread (recruiter <-> candidate)."""
    app = _authorised_application(db, user, application_id)
    is_candidate = user.role == UserRole.candidate
    if is_candidate and payload.message_type != MessageType.message:
        raise HTTPException(status_code=403, detail="Candidates can only send regular messages")

    msg = ApplicationMessage(
        application_id=application_id,
        sender_id=user.id,
        message_type=payload.message_type,
        content=payload.content.strip(),
    )
    db.add(msg)

    # Interview invites, offers etc. move the application only if the ATS rules allow it
    target = None if is_candidate else _STATUS_FOR_TYPE.get(payload.message_type)
    status_changed = None
    if target and ats.check_transition(ApplicationStatus(app.status), target) is None:
        old = ats.change_status(db, app, target, user.id, note=f"via {payload.message_type.value} message")
        status_changed = (old.value, target.value)
        audit(db, "application.status_changed", actor=user, entity_type="application", entity_id=app.id,
              details={"from": old.value, "to": target.value, "via": "message"}, request=request)

    db.commit()
    db.refresh(msg)

    # ── Email notification to the recipient ──────────────────────────────────
    try:
        from app.services.email import send_message_notification_email
        job = app.job
        job_title = job.title if job else f"Job #{app.job_id}"
        if not is_candidate:
            candidate = db.query(Candidate).options(joinedload(Candidate.user)).filter(
                Candidate.id == app.candidate_id).first()
            if candidate and candidate.user:
                send_message_notification_email(
                    to_email=candidate.user.email,
                    to_name=candidate.user.name,
                    sender_name=user.name,
                    job_title=job_title,
                    message_type=payload.message_type.value,
                    content=payload.content,
                )
        elif job:
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

    if status_changed:
        logger.info("application %s moved %s -> %s by message", app.id, *status_changed)
    return _to_response(msg)


@router.get("/applications/{application_id}", response_model=list[MessageResponse])
def get_application_messages(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All messages for an application (only for the people on that application)."""
    _authorised_application(db, user, application_id)
    messages = (
        db.query(ApplicationMessage)
        .options(joinedload(ApplicationMessage.sender))
        .filter(ApplicationMessage.application_id == application_id)
        .order_by(ApplicationMessage.created_at.asc(), ApplicationMessage.id.asc())
        .all()
    )
    return [_to_response(m) for m in messages]


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

    rows = (
        db.query(ApplicationMessage, Application, Job)
        .join(Application, Application.id == ApplicationMessage.application_id)
        .join(Job, Job.id == Application.job_id)
        .options(joinedload(ApplicationMessage.sender))
        .filter(Application.candidate_id == candidate.id, ApplicationMessage.sender_id != user.id)
        .order_by(ApplicationMessage.created_at.desc(), ApplicationMessage.id.desc())
        .limit(500)
        .all()
    )
    return [{
        "id": msg.id,
        "application_id": app.id,
        "job_id": app.job_id,
        "job_title": job.title,
        "sender_name": msg.sender.name if msg.sender else "Recruiter",
        "message_type": msg.message_type,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
        "status": app.status,
    } for msg, app, job in rows]
