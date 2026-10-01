"""Billing rules: MOU fee terms -> placement fee -> invoice -> incentives.

All money is computed here on the server from stored terms; no endpoint accepts
a fee or incentive amount from the client (the owner can override an invoice
amount, with a mandatory reason that is audited).
"""
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import utc
from app.models import (
    Agreement, AgreementStatus, FeeType, Incentive, IncentiveRule, IncentiveStatus, Invoice, Placement, User,
    UserRole,
)

DEFAULT_INCENTIVE_RATES = {UserRole.hr: 5.0, UserRole.bdm: 5.0, UserRole.owner: 0.0}


def compute_fee(fee_type: FeeType, fee_value: float, ctc: float) -> float:
    if fee_type == FeeType.percentage:
        return round((ctc or 0) * fee_value / 100.0, 2)
    return round(fee_value, 2)


async def active_agreement_for(db: AsyncSession, company_id: int, on: datetime) -> Agreement | None:
    rows = (await db.execute(
        select(Agreement).where(Agreement.company_id == company_id, Agreement.status == AgreementStatus.active)
        .order_by(Agreement.start_date.desc())
    )).scalars().all()
    on = utc(on)
    for a in rows:
        if utc(a.start_date) <= on and (a.end_date is None or utc(a.end_date) >= on):
            return a
    return None


async def next_invoice_number(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"{settings.INVOICE_PREFIX}-{year}-"
    last = (await db.execute(
        select(func.max(Invoice.invoice_number)).where(Invoice.invoice_number.like(f"{prefix}%"))
    )).scalar()
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


def gst_split(amount: float) -> tuple[float, float, float]:
    rate = settings.GST_RATE_PERCENT
    gst = round(amount * rate / 100.0, 2)
    return rate, gst, round(amount + gst, 2)


async def incentive_rate(db: AsyncSession, role: UserRole) -> float:
    rule = (await db.execute(select(IncentiveRule).where(IncentiveRule.role == role))).scalar_one_or_none()
    return rule.percentage if rule else DEFAULT_INCENTIVE_RATES.get(role, 0.0)


async def create_incentives(db: AsyncSession, invoice: Invoice, placement: Placement) -> list[Incentive]:
    """One incentive per credited team member (recruiter, BDM) on a paid invoice."""
    created = []
    seen = set()
    for user_id in (placement.recruiter_id, placement.bdm_id):
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        user = await db.get(User, user_id)
        if not user:
            continue
        exists = (await db.execute(select(Incentive).where(
            Incentive.invoice_id == invoice.id, Incentive.user_id == user_id))).scalar_one_or_none()
        if exists:
            continue
        rate = await incentive_rate(db, user.role)
        if rate <= 0:
            continue
        inc = Incentive(user_id=user_id, placement_id=placement.id, invoice_id=invoice.id, role=user.role,
                        basis_amount=invoice.amount, rate=rate, amount=round(invoice.amount * rate / 100.0, 2),
                        status=IncentiveStatus.pending)
        db.add(inc)
        created.append(inc)
    return created


async def void_incentives(db: AsyncSession, reason: str, invoice_id: int | None = None,
                          placement_id: int | None = None) -> int:
    stmt = update(Incentive).where(Incentive.status.in_([IncentiveStatus.pending, IncentiveStatus.approved]))
    if invoice_id:
        stmt = stmt.where(Incentive.invoice_id == invoice_id)
    if placement_id:
        stmt = stmt.where(Incentive.placement_id == placement_id)
    res = await db.execute(stmt.values(status=IncentiveStatus.void, void_reason=reason,
                                       updated_at=datetime.now(timezone.utc)))
    return res.rowcount or 0


async def seed_incentive_rules(db: AsyncSession) -> None:
    existing = {r.role for r in (await db.execute(select(IncentiveRule))).scalars().all()}
    for role, pct in DEFAULT_INCENTIVE_RATES.items():
        if role not in existing:
            db.add(IncentiveRule(role=role, percentage=pct))
    await db.commit()
