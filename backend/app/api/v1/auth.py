import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    hash_password,
    hash_reset_token,
    hash_token_id,
    new_token_id,
    utc,
    verify_password,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import (
    client_ip,
    forgot_email_limiter,
    forgot_ip_limiter,
    login_ip_limiter,
    register_ip_limiter,
)
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.password_reset import PasswordResetToken
from app.models.recruiter import Recruiter
from app.models.session import UserSession
from app.models.user import User, UserRole
from app.schemas.auth import (
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.audit import audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_FORGOT = "If an account exists for this email, reset instructions have been sent."
SESSION_ENDED = "Your session has ended. Please sign in again."


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _start_session(db: Session, user: User, request: Request) -> AuthSuccessResponse:
    """Create a device session and return its access + refresh tokens."""
    jti = new_token_id()
    session = UserSession(
        user_id=user.id,
        refresh_jti_hash=hash_token_id(jti),
        device_info=(request.headers.get("User-Agent") or "")[:255],
        ip_address=client_ip(request),
        last_used_at=_now(),
        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.flush()
    return AuthSuccessResponse(
        access_token=create_access_token(str(user.id), session.id),
        refresh_token=create_refresh_token(str(user.id), session.id, jti),
        user=UserResponse.model_validate(user),
    )


def _revoke_sessions(db: Session, user_id: int, except_session_id: int | None = None) -> int:
    q = db.query(UserSession).filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
    if except_session_id is not None:
        q = q.filter(UserSession.id != except_session_id)
    return q.update({UserSession.revoked_at: _now()}, synchronize_session=False)


@router.post("/register", response_model=AuthSuccessResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    register_ip_limiter.check(client_ip(request), "Too many sign-ups from this network. Please try again later.")
    email = str(payload.email).lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(name=payload.name.strip(), email=email,
                password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()

    if payload.role == UserRole.candidate:
        db.add(Candidate(user_id=user.id))
    elif payload.role in (UserRole.recruiter, UserRole.company_admin):
        company = Company(name=payload.company_name or "My Organization")
        db.add(company)
        db.flush()
        db.add(Recruiter(user_id=user.id, company_id=company.id))

    result = _start_session(db, user, request)
    audit(db, "auth.register", actor=user, entity_type="user", entity_id=user.id,
          details={"role": user.role.value}, request=request)
    db.commit()
    try:
        from app.services.email import send_welcome_email
        send_welcome_email(user.email, user.name)
    except Exception:
        logger.exception("welcome email failed")
    return result


@router.post("/login", response_model=AuthSuccessResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    login_ip_limiter.check(client_ip(request), "Too many sign-in attempts from this network. Please wait a minute.")
    email = str(payload.email).lower()
    user = db.query(User).filter(User.email == email).first()

    if user and user.locked_until and utc(user.locked_until) > _now():
        minutes = max(1, int((utc(user.locked_until) - _now()).total_seconds() // 60) + 1)
        raise HTTPException(status_code=423, detail=(
            f"Too many failed sign-in attempts. This account is locked for {minutes} more minute(s). "
            "You can also reset your password."))

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.LOGIN_MAX_FAILURES:
                user.locked_until = _now() + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                user.failed_login_count = 0
                audit(db, "auth.account_locked", actor=user, entity_type="user", entity_id=user.id, request=request)
            else:
                audit(db, "auth.login_failed", actor=user, entity_type="user", entity_id=user.id, request=request)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.is_active is False:
        raise HTTPException(status_code=403, detail="This account has been deactivated. Contact support.")

    user.failed_login_count, user.locked_until, user.last_login_at = 0, None, _now()
    result = _start_session(db, user, request)
    audit(db, "auth.login", actor=user, entity_type="user", entity_id=user.id, request=request)
    db.commit()
    return result


@router.post("/refresh", response_model=AuthSuccessResponse)
def refresh_token(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    data = decode_token_safe(payload.refresh_token)
    if not data or data.get("type") != "refresh" or not all(k in data for k in ("sub", "sid", "jti")):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    session = db.get(UserSession, int(data["sid"]))
    if (not session or session.user_id != int(data["sub"]) or session.revoked_at is not None
            or utc(session.expires_at) < _now()):
        raise HTTPException(status_code=401, detail=SESSION_ENDED)
    user = db.get(User, session.user_id)
    if not user or user.is_active is False:
        raise HTTPException(status_code=401, detail=SESSION_ENDED)

    if hash_token_id(data["jti"]) != session.refresh_jti_hash:
        # An old refresh token was replayed: assume it was stolen and end the session.
        session.revoked_at = _now()
        audit(db, "auth.refresh_token_reuse", actor=user, entity_type="session",
              entity_id=session.id, request=request)
        db.commit()
        raise HTTPException(status_code=401, detail=SESSION_ENDED)

    jti = new_token_id()
    session.refresh_jti_hash = hash_token_id(jti)
    session.last_used_at = _now()
    db.commit()
    return AuthSuccessResponse(
        access_token=create_access_token(str(user.id), session.id),
        refresh_token=create_refresh_token(str(user.id), session.id, jti),
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(UserSession, request.state.session_id)
    if session and session.revoked_at is None:
        session.revoked_at = _now()
    audit(db, "auth.logout", actor=user, entity_type="session", entity_id=request.state.session_id, request=request)
    db.commit()
    return {"message": "Signed out"}


@router.post("/logout-all")
def logout_all(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = _revoke_sessions(db, user.id)
    audit(db, "auth.logout_all", actor=user, entity_type="user", entity_id=user.id,
          details={"sessions_ended": count}, request=request)
    db.commit()
    return {"message": f"Signed out of {count} device(s)"}


@router.get("/sessions")
def list_sessions(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(UserSession)
            .filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_used_at.desc()).all())
    now = _now()
    return [{
        "id": s.id, "device_info": s.device_info, "ip_address": s.ip_address,
        "created_at": s.created_at, "last_used_at": s.last_used_at,
        "current": s.id == request.state.session_id,
    } for s in rows if utc(s.expires_at) > now]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: int, request: Request, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    session = db.get(UserSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.revoked_at is None:
        session.revoked_at = _now()
    audit(db, "auth.session_revoked", actor=user, entity_type="session", entity_id=session_id, request=request)
    db.commit()
    return {"message": "Device signed out"}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, request: Request,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    ended = _revoke_sessions(db, user.id, except_session_id=request.state.session_id)
    audit(db, "auth.password_changed", actor=user, entity_type="user", entity_id=user.id,
          details={"other_sessions_ended": ended}, request=request)
    db.commit()
    return {"message": "Password changed. Other devices have been signed out."}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    forgot_ip_limiter.check(client_ip(request), "Too many reset requests. Please try again in a few minutes.")
    forgot_email_limiter.check(email, "A reset email was sent recently. Please check your inbox and spam folder.")
    user = db.query(User).filter(User.email == email).first()
    if not user or user.is_active is False:
        return {"message": GENERIC_FORGOT}

    raw = secrets.token_urlsafe(32)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hash_reset_token(raw),
                              expires_at=_now() + timedelta(hours=1)))
    audit(db, "auth.password_reset_requested", actor=user, entity_type="user", entity_id=user.id, request=request)
    db.commit()

    from app.services.email import send_password_reset_email
    send_password_reset_email(user.email, user.name, raw)
    return {"message": GENERIC_FORGOT, "reset_token": raw if settings.DEBUG else None}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    row = (db.query(PasswordResetToken)
           .filter(PasswordResetToken.token_hash == hash_reset_token(payload.token),
                   PasswordResetToken.used_at.is_(None))
           .first())
    if not row or utc(row.expires_at) < _now():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    user.password_hash = hash_password(payload.new_password)
    user.failed_login_count, user.locked_until = 0, None
    row.used_at = _now()
    ended = _revoke_sessions(db, user.id)
    audit(db, "auth.password_reset", actor=user, entity_type="user", entity_id=user.id,
          details={"sessions_ended": ended}, request=request)
    db.commit()
    return {"message": "Password has been reset. You can sign in with your new password."}
