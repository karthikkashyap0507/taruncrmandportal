"""Audit trail and notifications helpers used by every CRM endpoint."""
import asyncio
import enum
import logging
from datetime import date, datetime
from typing import Iterable

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog, ActivityType, Notification, NotifType, User

logger = logging.getLogger(__name__)


def _plain(value):
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def diff(obj, changes: dict) -> dict:
    """{field: {"from": old, "to": new}} for fields whose value actually changes."""
    out = {}
    for field, new in changes.items():
        old = getattr(obj, field, None)
        if _plain(old) != _plain(new):
            out[field] = {"from": _plain(old), "to": _plain(new)}
    return out


def log_activity(
    db: AsyncSession,
    user: User,
    action: ActivityType,
    description: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    changes: dict | None = None,
    request: Request | None = None,
) -> None:
    """Record an audit entry in the current transaction (committed with the change)."""
    db.add(ActivityLog(
        user_id=user.id,
        action=action,
        description=description[:2000],
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes or None,
        ip_address=(request.client.host if request and request.client else None),
    ))


def notify(db: AsyncSession, user_ids: Iterable[int | None], title: str, body: str,
           type_: NotifType = NotifType.system, action_url: str | None = None,
           exclude: int | None = None) -> list[int]:
    """Add in-app notifications (committed with the current transaction). Returns
    the recipients so callers can also send email after committing."""
    seen = []
    for uid in user_ids:
        if uid and uid != exclude and uid not in seen:
            seen.append(uid)
            db.add(Notification(user_id=uid, title=title[:255], body=body, type=type_, action_url=action_url))
    return seen


async def email_users(db: AsyncSession, user_ids: Iterable[int], title: str, body: str,
                      url: str | None = None, category: str = "notification") -> None:
    """Email twin of in-app notifications; call after commit."""
    from sqlalchemy import select
    from app.services.email import send_notification_email
    ids = [u for u in user_ids if u]
    if not ids:
        return
    users = (await db.execute(select(User).where(User.id.in_(ids), User.is_active == True))).scalars().all()  # noqa: E712
    for u in users:
        await asyncio.to_thread(send_notification_email, u.email, u.name, title, body, url, category)


async def queue_email(func, *args) -> None:
    """Run one of the email.send_* functions (they enqueue into the outbox) off the event loop."""
    try:
        await asyncio.to_thread(func, *args)
    except Exception:
        logger.exception("could not queue email via %s", getattr(func, "__name__", func))
