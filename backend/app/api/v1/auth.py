import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.core.config import settings
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.password_reset import PasswordResetToken
from app.models.recruiter import Recruiter
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

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for_user(user: User) -> tuple[str, str]:
    return create_access_token(str(user.id)), create_refresh_token(str(user.id))


@router.post("/register", response_model=AuthSuccessResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == str(payload.email).lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()

    if payload.role == UserRole.candidate:
        db.add(Candidate(user_id=user.id))
    elif payload.role in (UserRole.recruiter, UserRole.company_admin):
        company = Company(
            name=payload.company_name or "My Organization",
            logo=None,
            website=None,
            description=None,
            industry=None,
        )
        db.add(company)
        db.flush()
        db.add(Recruiter(user_id=user.id, company_id=company.id))

    db.commit()
    db.refresh(user)

    access, refresh = _tokens_for_user(user)
    return AuthSuccessResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthSuccessResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access, refresh = _tokens_for_user(user)
    return AuthSuccessResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=AuthSuccessResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token_safe(payload.refresh_token)
    if not data or data.get("type") != "refresh" or "sub" not in data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        user_id = int(data["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access, refresh = _tokens_for_user(user)
    return AuthSuccessResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).lower()).first()
    if not user:
        return {"message": "If an account exists for this email, reset instructions have been sent."}

    raw = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
        )
    )
    db.commit()

    # In production, send email with link: {FRONTEND_URL}/auth/reset-password?token={raw}
    return {
        "message": "If an account exists for this email, reset instructions have been sent.",
        "reset_token": raw if settings.DEBUG else None,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    th = hash_reset_token(payload.token)
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == th,
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    user.password_hash = hash_password(payload.new_password)
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Password has been reset. You can sign in with your new password."}
