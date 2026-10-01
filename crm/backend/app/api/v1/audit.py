"""Owner-only views: the audit trail and the email delivery log (with retry)."""
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_owner
from app.models import ActivityLog, ActivityType, EmailOutbox, User
from app.services import outbox
from app.services.activity import log_activity

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
async def list_audit_logs(
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[ActivityType] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    q = select(ActivityLog, User.name, User.email).join(User, User.id == ActivityLog.user_id)
    if user_id:
        q = q.where(ActivityLog.user_id == user_id)
    if entity_type:
        q = q.where(ActivityLog.entity_type == entity_type)
    if entity_id:
        q = q.where(ActivityLog.entity_id == entity_id)
    if action:
        q = q.where(ActivityLog.action == action)
    if since:
        q = q.where(ActivityLog.created_at >= since)
    if until:
        q = q.where(ActivityLog.created_at <= until)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(ActivityLog.id.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {"total": total, "page": page, "limit": limit, "data": [{
        "id": log.id, "created_at": log.created_at.isoformat(), "user_id": log.user_id, "user_name": name,
        "user_email": email, "action": log.action.value, "description": log.description,
        "entity_type": log.entity_type, "entity_id": log.entity_id, "changes": log.changes,
        "ip_address": log.ip_address,
    } for log, name, email in rows]}


@router.get("/notifications/deliveries")
async def list_deliveries(
    status: Optional[str] = Query(None, description="pending | sent | failed | dead"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    q = select(EmailOutbox)
    if status:
        q = q.where(EmailOutbox.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(EmailOutbox.id.desc()).offset((page - 1) * limit).limit(limit))).scalars()
    counts = dict((await db.execute(select(EmailOutbox.status, func.count(EmailOutbox.id))
                                    .group_by(EmailOutbox.status))).all())
    return {"total": total, "page": page, "limit": limit, "counts": counts, "data": [{
        "id": r.id, "category": r.category, "to_email": r.to_email, "subject": r.subject, "status": r.status,
        "attempts": r.attempts, "last_error": r.last_error,
        "next_attempt_at": r.next_attempt_at.isoformat() if r.next_attempt_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "sent_at": r.sent_at.isoformat() if r.sent_at else None,
    } for r in rows.all()]}


@router.post("/notifications/deliveries/{outbox_id}/retry")
async def retry_delivery(outbox_id: int, request: Request, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(require_owner)):
    row = await db.get(EmailOutbox, outbox_id)
    if not row:
        raise HTTPException(404, "Email not found")
    if row.status == "sent":
        return {"message": "Already sent", "status": "sent"}
    log_activity(db, current_user, ActivityType.email_sent, f"Retried email #{outbox_id} to {row.to_email}",
                 "email", outbox_id, request=request)
    await db.commit()
    ok = await asyncio.to_thread(outbox.deliver, outbox_id, True)
    await db.refresh(row)
    return {"message": "Sent" if ok else "Still failing", "status": row.status, "last_error": row.last_error}


@router.post("/notifications/deliveries/retry-failed")
async def retry_all_failed(request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_owner)):
    ids = list((await db.execute(select(EmailOutbox.id).where(EmailOutbox.status.in_(["failed", "dead"]))
                                 .limit(200))).scalars())
    log_activity(db, current_user, ActivityType.email_sent, f"Retried {len(ids)} failed email(s)", "email", None,
                 request=request)
    await db.commit()
    results = [await asyncio.to_thread(outbox.deliver, i, True) for i in ids]
    return {"attempted": len(ids), "sent": sum(results), "still_failing": len(ids) - sum(results)}
