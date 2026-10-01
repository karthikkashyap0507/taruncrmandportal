"""Incentives (royalty/commission payouts) for the team.

Incentives are only ever created by the server when an invoice is paid, from the
owner-defined rate for the credited person's role. There is deliberately no
endpoint to create an incentive or edit its amount. Owners approve, pay or void;
everyone else can only see their own.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, is_owner, require_owner
from app.models import ActivityType, Incentive, IncentiveRule, IncentiveStatus, Invoice, NotifType, User, UserRole
from app.services.activity import log_activity, notify

router = APIRouter(prefix="/incentives", tags=["incentives"])


class RuleUpdate(BaseModel):
    percentage: float = Field(..., ge=0, le=50)


class VoidRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


def _serialize(i: Incentive, user_name: str | None = None, invoice_number: str | None = None) -> dict:
    return {
        "id": i.id,
        "user_id": i.user_id,
        "user_name": user_name,
        "placement_id": i.placement_id,
        "invoice_id": i.invoice_id,
        "invoice_number": invoice_number,
        "role": i.role.value,
        "basis_amount": i.basis_amount,
        "rate": i.rate,
        "amount": i.amount,
        "status": i.status.value,
        "void_reason": i.void_reason,
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rules = (await db.execute(select(IncentiveRule).order_by(IncentiveRule.role))).scalars().all()
    return [{"role": r.role.value, "percentage": r.percentage,
             "updated_at": r.updated_at.isoformat() if r.updated_at else None} for r in rules]


@router.put("/rules/{role}")
async def update_rule(role: UserRole, payload: RuleUpdate, request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(require_owner)):
    rule = (await db.execute(select(IncentiveRule).where(IncentiveRule.role == role))).scalar_one_or_none()
    old = rule.percentage if rule else None
    if not rule:
        rule = IncentiveRule(role=role, percentage=payload.percentage)
        db.add(rule)
    rule.percentage = payload.percentage
    rule.updated_by_id = current_user.id
    rule.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.update, f"Incentive rate for {role.value}: {old} -> {payload.percentage}%",
                 "incentive_rule", None, changes={"role": role.value, "from": old, "to": payload.percentage},
                 request=request)
    await db.commit()
    return {"role": role.value, "percentage": rule.percentage}


@router.get("/")
async def list_incentives(
    status: Optional[IncentiveStatus] = None,
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (select(Incentive, User.name, Invoice.invoice_number)
         .join(User, User.id == Incentive.user_id)
         .join(Invoice, Invoice.id == Incentive.invoice_id))
    if not is_owner(current_user):
        q = q.where(Incentive.user_id == current_user.id)   # everyone else sees only their own
    elif user_id:
        q = q.where(Incentive.user_id == user_id)
    if status:
        q = q.where(Incentive.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(Incentive.id.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize(i, n, num) for i, n, num in rows]}


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = select(Incentive.status, func.count(Incentive.id), func.coalesce(func.sum(Incentive.amount), 0)) \
        .group_by(Incentive.status)
    if not is_owner(current_user):
        q = q.where(Incentive.user_id == current_user.id)
    rows = (await db.execute(q)).all()
    out = {s.value: {"count": 0, "amount": 0.0} for s in IncentiveStatus}
    for status, count, amount in rows:
        out[status.value] = {"count": count, "amount": round(float(amount), 2)}
    return out


async def _transition(db: AsyncSession, incentive_id: int, target: IncentiveStatus, allowed_from: set,
                      actor: User, request: Request, reason: str | None = None) -> Incentive:
    inc = await db.get(Incentive, incentive_id)
    if not inc:
        raise HTTPException(404, "Incentive not found")
    if inc.status not in allowed_from:
        raise HTTPException(409, f"An incentive that is {inc.status.value} cannot be marked {target.value}")
    old = inc.status
    inc.status = target
    inc.updated_at = datetime.now(timezone.utc)
    if target == IncentiveStatus.approved:
        inc.approved_by_id = actor.id
    if reason:
        inc.void_reason = reason
    log_activity(db, actor, ActivityType.approve if target != IncentiveStatus.void else ActivityType.update,
                 f"Incentive #{inc.id}: {old.value} -> {target.value}", "incentive", inc.id,
                 changes={"status": {"from": old.value, "to": target.value}, "reason": reason}, request=request)
    notify(db, [inc.user_id], f"Incentive {target.value}", f"INR {inc.amount:,.2f}", NotifType.incentive,
           "/incentives", exclude=actor.id)
    await db.commit()
    return inc


@router.post("/{incentive_id}/approve")
async def approve(incentive_id: int, request: Request, db: AsyncSession = Depends(get_db),
                  current_user: User = Depends(require_owner)):
    inc = await _transition(db, incentive_id, IncentiveStatus.approved, {IncentiveStatus.pending}, current_user, request)
    return _serialize(inc)


@router.post("/{incentive_id}/mark-paid")
async def mark_paid(incentive_id: int, request: Request, db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(require_owner)):
    inc = await _transition(db, incentive_id, IncentiveStatus.paid, {IncentiveStatus.approved}, current_user, request)
    return _serialize(inc)


@router.post("/{incentive_id}/void")
async def void(incentive_id: int, payload: VoidRequest, request: Request, db: AsyncSession = Depends(get_db),
               current_user: User = Depends(require_owner)):
    inc = await _transition(db, incentive_id, IncentiveStatus.void,
                            {IncentiveStatus.pending, IncentiveStatus.approved}, current_user, request, payload.reason)
    return _serialize(inc)
