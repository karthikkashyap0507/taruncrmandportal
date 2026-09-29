from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update
from pydantic import BaseModel, EmailStr, field_validator
import re

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, generate_reset_token,
)
from app.models import User, UserSession, PasswordResetToken, UserRole, ActivityLog, ActivityType
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: UserRole = UserRole.hr

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    credential: str  # email or phone
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

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


async def _log_activity(db: AsyncSession, user_id: int, action: ActivityType, desc: str, ip: str = None):
    log = ActivityLog(user_id=user_id, action=action, description=desc, ip_address=ip)
    db.add(log)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Public sign-up only creates the first account, which becomes the owner.
    # After that, the owner adds team members from the Team page.
    if await db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(
            status_code=403,
            detail="Registration is closed. Ask your CRM owner to add you from the Team page.",
        )

    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check phone uniqueness
    if payload.phone:
        result = await db.execute(select(User).where(User.phone == payload.phone))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole.owner,
        is_active=True,
        is_verified=True,  # No OTP per requirements
        login_count=1,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await _log_activity(db, user.id, ActivityType.login, f"New registration from {payload.email}")
    await db.commit()
    await db.refresh(user)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=_user_dict(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Try email or phone
    is_email = "@" in payload.credential
    if is_email:
        result = await db.execute(select(User).where(User.email == payload.credential))
    else:
        result = await db.execute(select(User).where(User.phone == payload.credential))

    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact your administrator.")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    user.login_count = (user.login_count or 0) + 1

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await _log_activity(db, user.id, ActivityType.login, f"Login from {request.client.host if request.client else 'unknown'}")
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=_user_dict(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token == payload.refresh_token,
            UserSession.is_active == True,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        session.is_active = False
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user_result = await db.execute(select(User).where(User.id == int(data["sub"])))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    new_access = create_access_token({"sub": str(user.id), "role": user.role.value})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    session.refresh_token = new_refresh
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh, user=_user_dict(user))


@router.post("/logout")
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(UserSession)
        .where(UserSession.refresh_token == payload.refresh_token)
        .values(is_active=False)
    )
    await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user:
        token = generate_reset_token(payload.email)
        reset = PasswordResetToken(
            email=payload.email,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(reset)
        await db.commit()
        # Send email async (import here to avoid circular)
        try:
            from app.services.email import send_password_reset_email
            send_password_reset_email(payload.email, user.name, token)
        except Exception:
            pass
    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.token)
    if not data or data.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == payload.token,
            PasswordResetToken.used == False,
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise HTTPException(status_code=400, detail="Token already used or invalid")

    if reset.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")

    user_result = await db.execute(select(User).where(User.email == data["sub"]))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")

    user.password_hash = hash_password(payload.new_password)
    reset.used = True
    # Invalidate all sessions
    await db.execute(update(UserSession).where(UserSession.user_id == user.id).values(is_active=False))
    await db.commit()
    return {"message": "Password reset successfully. Please log in."}


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db), user: User = Depends(lambda: None)):
    # This is handled by the dependency in actual routes
    pass
