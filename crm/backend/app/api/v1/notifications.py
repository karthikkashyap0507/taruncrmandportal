from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Notification, User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(n: Notification) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body,
        "type": n.type.value,
        "read": n.read,
        "action_url": n.action_url,
        "created_at": n.created_at.isoformat(),
    }


@router.get("/")
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.read == False)
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [_serialize(n) for n in result.scalars().all()]


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.read == False,
        )
    )
    return {"count": result.scalar()}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(read=True)
    )
    await db.commit()
    return {"message": "Marked as read"}


@router.patch("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}
