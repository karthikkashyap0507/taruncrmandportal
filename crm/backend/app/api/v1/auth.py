from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import client_ip, forgot_email_limiter, forgot_ip_limiter, login_ip_limiter, register_ip_limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    utc,
    verify_password,
)
from app.models import ActivityType, PasswordResetToken, User, UserRole, UserSession
from app.services.activity import log_activity, queue_email

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_ENDED = "Your session has ended. Please sign in again."


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(..., max_length=128)
    role: UserRole = UserRole.hr

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    credential: str = Field(..., min_length=1, max_length=255)  # email or phone
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.value,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "permissions": user.permissions or {},
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


async def _start_session(db: AsyncSession, user: User, request: Request) -> TokenResponse:
    """Create a device session; both tokens carry its id so it can be revoked."""
    session = UserSession(
        user_id=user.id,
        refresh_token=f"pending-{user.id}-{_now().timestamp()}-{id(request)}",
        device_info=(request.headers.get("User-Agent") or "")[:255],
        ip_address=client_ip(request),
        last_used_at=_now(),
        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()
    claims = {"sub": str(user.id), "sid": session.id}
    session.refresh_token = create_refresh_token(claims)
    access = create_access_token({**claims, "role": user.role.value})
    return TokenResponse(access_token=access, refresh_token=session.refresh_token, user=_user_dict(user))


async def _revoke_all(db: AsyncSession, user_id: int, except_session_id: int | None = None) -> None:
    stmt = update(UserSession).where(UserSession.user_id == user_id, UserSession.is_active == True)  # noqa: E712
    if except_session_id is not None:
        stmt = stmt.where(UserSession.id != except_session_id)
    await db.execute(stmt.values(is_active=False))


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    register_ip_limiter.check(client_ip(request), "Too many sign-ups from this network. Please try again later.")
    # Public sign-up only creates the first account, which becomes the owner.
    # After that, the owner adds team members from the Team page.
    if await db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(
            status_code=403,
            detail="Registration is closed. Ask your CRM owner to add you from the Team page.",
        )
    email = payload.email.lower()
    user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole.owner,
        is_active=True,
        is_verified=True,
        login_count=1,
        last_login=_now(),
    )
    db.add(user)
    await db.flush()
    result = await _start_session(db, user, request)
    log_activity(db, user, ActivityType.create, f"Owner account created: {email}", "user", user.id, request=request)
    await db.commit()
    return result


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    login_ip_limiter.check(client_ip(request), "Too many sign-in attempts from this network. Please wait a minute.")
    credential = payload.credential.strip()
    if "@" in credential:
        user = (await db.execute(select(User).where(func.lower(User.email) == credential.lower()))).scalar_one_or_none()
    else:
        user = (await db.execute(select(User).where(User.phone == credential))).scalar_one_or_none()

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
                log_activity(db, user, ActivityType.security, "Account locked after repeated failed sign-ins",
                             "user", user.id, request=request)
            else:
                log_activity(db, user, ActivityType.security, "Failed sign-in attempt", "user", user.id,
                             request=request)
            await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact your administrator.")

    user.failed_login_count, user.locked_until = 0, None
    user.last_login = _now()
    user.login_count = (user.login_count or 0) + 1
    result = await _start_session(db, user, request)
    log_activity(db, user, ActivityType.login, f"Login from {client_ip(request)}", "user", user.id, request=request)
    await db.commit()
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh" or "sid" not in data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    session = await db.get(UserSession, int(data["sid"]))
    if not session or not session.is_active or session.user_id != int(data["sub"]):
        raise HTTPException(status_code=401, detail=SESSION_ENDED)
    if utc(session.expires_at) < _now():
        session.is_active = False
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")
    user = await db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if session.refresh_token != payload.refresh_token:
        # An already-used refresh token was replayed: treat as stolen, end the session
        session.is_active = False
        log_activity(db, user, ActivityType.security, "Refresh token reuse detected; session ended",
                     "session", session.id, request=request)
        await db.commit()
        raise HTTPException(status_code=401, detail=SESSION_ENDED)

    claims = {"sub": str(user.id), "sid": session.id}
    session.refresh_token = create_refresh_token(claims)
    session.last_used_at = _now()
    await db.commit()
    return TokenResponse(access_token=create_access_token({**claims, "role": user.role.value}),
                         refresh_token=session.refresh_token, user=_user_dict(user))


@router.post("/logout")
async def logout(payload: LogoutRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Ends the session belonging to the given refresh token (sent by the app on sign-out)."""
    if payload.refresh_token:
        data = decode_token(payload.refresh_token)
        if data and data.get("sid"):
            await db.execute(update(UserSession).where(UserSession.id == int(data["sid"])).values(is_active=False))
        await db.execute(update(UserSession).where(UserSession.refresh_token == payload.refresh_token)
                         .values(is_active=False))
        await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _revoke_all(db, user.id)
    log_activity(db, user, ActivityType.logout, "Signed out of all devices", "user", user.id, request=request)
    await db.commit()
    return {"message": "Signed out of all devices"}


@router.get("/sessions")
async def list_sessions(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.is_active == True)  # noqa: E712
        .order_by(UserSession.last_used_at.desc())
    )).scalars().all()
    now = _now()
    return [{
        "id": s.id, "device_info": s.device_info, "ip_address": s.ip_address,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        "current": s.id == request.state.session_id,
    } for s in rows if utc(s.expires_at) > now]


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: int, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    session = await db.get(UserSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_active = False
    log_activity(db, user, ActivityType.logout, f"Signed out device #{session_id}", "session", session_id,
                 request=request)
    await db.commit()
    return {"message": "Device signed out"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return _user_dict(user)


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, request: Request,
                          user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await _revoke_all(db, user.id, except_session_id=request.state.session_id)
    log_activity(db, user, ActivityType.security, "Password changed; other devices signed out", "user", user.id,
                 request=request)
    await db.commit()
    return {"message": "Password changed. Other devices have been signed out."}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower()
    forgot_ip_limiter.check(client_ip(request), "Too many reset requests. Please try again in a few minutes.")
    forgot_email_limiter.check(email, "A reset email was sent recently. Please check your inbox and spam folder.")
    user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
    if user and user.is_active:
        token = generate_reset_token(user.email)
        db.add(PasswordResetToken(email=user.email, token=token, expires_at=_now() + timedelta(hours=1)))
        log_activity(db, user, ActivityType.security, "Password reset requested", "user", user.id, request=request)
        await db.commit()
        from app.services.email import send_password_reset_email
        await queue_email(send_password_reset_email, user.email, user.name, token)
    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.token)
    if not data or data.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    reset = (await db.execute(select(PasswordResetToken).where(
        PasswordResetToken.token == payload.token, PasswordResetToken.used == False))).scalar_one_or_none()  # noqa: E712
    if not reset:
        raise HTTPException(status_code=400, detail="Token already used or invalid")
    if utc(reset.expires_at) < _now():
        raise HTTPException(status_code=400, detail="Token expired")
    user = (await db.execute(select(User).where(User.email == data["sub"]))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    user.failed_login_count, user.locked_until = 0, None
    reset.used = True
    await _revoke_all(db, user.id)
    log_activity(db, user, ActivityType.security, "Password reset; all devices signed out", "user", user.id,
                 request=request)
    await db.commit()
    return {"message": "Password reset successfully. Please log in."}
