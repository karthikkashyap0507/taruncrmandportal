from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner
from app.core.security import hash_password
from app.models import User, UserRole, ActivityLog, ActivityType, UserSession
from app.services.activity import diff, log_activity, queue_email

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole
    permissions: Optional[dict] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    permissions: Optional[dict] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    role: str
    is_active: bool
    permissions: Optional[dict]
    last_login: Optional[datetime]
    login_count: int
    created_at: datetime

    class Config:
        from_attributes = True


def _serialize(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "role": u.role.value,
        "avatar_url": u.avatar_url,
        "is_active": u.is_active,
        "permissions": u.permissions or {},
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "login_count": u.login_count or 0,
        "created_at": u.created_at.isoformat(),
    }


@router.get("/", response_model=List[dict])
async def list_users(
    role: Optional[str] = None,
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if search:
        query = query.where(User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    query = query.order_by(User.created_at.desc())
    result = await db.execute(query)
    return [_serialize(u) for u in result.scalars().all()]


@router.post("/", status_code=201)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    # Uniqueness checks
    email = payload.email.lower()
    existing = await db.execute(select(User).where(func.lower(User.email) == email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already exists")
    if payload.phone and (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none():
        raise HTTPException(400, "Phone number already exists")

    user = User(
        name=payload.name,
        email=email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        is_verified=True,
        permissions=payload.permissions or {},
    )
    db.add(user)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Added team member {email} ({payload.role.value})",
                 "user", user.id, request=request)
    await db.commit()
    await db.refresh(user)
    from app.services.email import send_welcome_email
    await queue_email(send_welcome_email, user.email, user.name)
    return _serialize(user)


@router.get("/directory")
async def user_directory(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Names and roles of active team members (for assignment dropdowns)."""
    rows = (await db.execute(select(User).where(User.is_active == True).order_by(User.name))).scalars().all()  # noqa: E712
    return [{"id": u.id, "name": u.name, "role": u.role.value} for u in rows]


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return _serialize(current_user)


class SelfUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)


@router.put("/me")
async def update_me(payload: SelfUpdate, request: Request, db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """Any user can edit their own name and phone (role and status stay owner-only)."""
    data = payload.model_dump(exclude_none=True)
    if data.get("phone") and data["phone"] != current_user.phone:
        taken = (await db.execute(select(User).where(User.phone == data["phone"], User.id != current_user.id))).scalar_one_or_none()
        if taken:
            raise HTTPException(400, "Phone number already exists")
    changes = diff(current_user, data)
    for k, v in data.items():
        setattr(current_user, k, v)
    if changes:
        log_activity(db, current_user, ActivityType.update, "Updated own profile", "user", current_user.id,
                     changes=changes, request=request)
    await db.commit()
    return _serialize(current_user)


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return _serialize(user)


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    if user_id == current_user.id and payload.role and payload.role != UserRole.owner:
        raise HTTPException(400, "Cannot change your own owner role")

    data = payload.model_dump(exclude_none=True)
    changes = diff(user, data)
    for field, val in data.items():
        setattr(user, field, val)
    if data.get("is_active") is False:
        await db.execute(update(UserSession).where(UserSession.user_id == user.id).values(is_active=False))
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated team member {user.email}",
                     "user", user.id, changes=changes, request=request)
    await db.commit()
    return _serialize(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    if user_id == current_user.id:
        raise HTTPException(400, "Cannot delete your own account")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    await db.execute(update(UserSession).where(UserSession.user_id == user.id).values(is_active=False))
    log_activity(db, current_user, ActivityType.delete, f"Deactivated team member {user.email}",
                 "user", user.id, request=request)
    await db.commit()
    return {"message": "User deactivated"}


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.user_id == user_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "action": l.action.value,
            "description": l.description,
            "changes": l.changes,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
