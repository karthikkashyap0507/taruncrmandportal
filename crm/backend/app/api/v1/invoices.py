"""Invoices: one per joined placement, priced from the placement's MOU terms."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import is_owner, require_owner, require_owner_or_bdm
from app.models import (
    ActivityType, Agreement, Candidate, Company, Contact, Invoice, InvoiceStatus, NotifType, Placement,
    PlacementStatus, User, UserRole,
)
from app.services import billing
from app.services.activity import log_activity, notify, queue_email

router = APIRouter(prefix="/invoices", tags=["invoices"])


class InvoiceCreate(BaseModel):
    placement_id: int
    issue_date: Optional[datetime] = None
    amount_override: Optional[float] = Field(default=None, gt=0, le=1_000_000_000)
    override_reason: Optional[str] = Field(default=None, max_length=1000)


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


def _serialize(i: Invoice, company_name: str | None = None, candidate_name: str | None = None) -> dict:
    return {
        "id": i.id,
        "invoice_number": i.invoice_number,
        "placement_id": i.placement_id,
        "agreement_id": i.agreement_id,
        "company_id": i.company_id,
        "company_name": company_name,
        "candidate_name": candidate_name,
        "amount": i.amount,
        "gst_rate": i.gst_rate,
        "gst_amount": i.gst_amount,
        "total_amount": i.total_amount,
        "amount_overridden": i.amount_overridden,
        "override_reason": i.override_reason,
        "issue_date": i.issue_date.isoformat() if i.issue_date else None,
        "due_date": i.due_date.isoformat() if i.due_date else None,
        "status": i.status.value,
        "paid_on": i.paid_on.isoformat() if i.paid_on else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


async def _get(db: AsyncSession, invoice_id: int) -> Invoice:
    inv = await db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv


@router.get("/")
async def list_invoices(
    status: Optional[InvoiceStatus] = None,
    company_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    q = (select(Invoice, Company.name, Candidate.name)
         .join(Company, Company.id == Invoice.company_id)
         .join(Placement, Placement.id == Invoice.placement_id)
         .join(Candidate, Candidate.id == Placement.candidate_id))
    if status:
        q = q.where(Invoice.status == status)
    if company_id:
        q = q.where(Invoice.company_id == company_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(Invoice.id.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize(i, c, n) for i, c, n in rows]}


@router.post("/", status_code=201)
async def raise_invoice(payload: InvoiceCreate, request: Request, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(require_owner_or_bdm)):
    p = await db.get(Placement, payload.placement_id)
    if not p:
        raise HTTPException(404, "Placement not found")
    if p.status != PlacementStatus.joined:
        raise HTTPException(409, "An invoice can only be raised after the candidate has joined")
    if (await db.execute(select(Invoice.id).where(Invoice.placement_id == p.id,
                                                  Invoice.status != InvoiceStatus.cancelled))).first():
        raise HTTPException(409, "This placement has already been invoiced")
    agreement = await db.get(Agreement, p.agreement_id)
    if not agreement:
        raise HTTPException(409, "This placement is not linked to an MOU")

    amount = p.fee_amount
    overridden = False
    if payload.amount_override is not None and round(payload.amount_override, 2) != round(p.fee_amount, 2):
        if not is_owner(current_user):
            raise HTTPException(403, "Only the owner can change an invoice amount from the MOU terms")
        if not payload.override_reason:
            raise HTTPException(422, "Give a reason for changing the invoice amount")
        amount, overridden = round(payload.amount_override, 2), True

    issue = payload.issue_date or datetime.now(timezone.utc)
    gst_rate, gst, total = billing.gst_split(amount)
    inv = Invoice(
        invoice_number=await billing.next_invoice_number(db), placement_id=p.id, agreement_id=agreement.id,
        company_id=p.company_id, amount=amount, gst_rate=gst_rate, gst_amount=gst, total_amount=total,
        amount_overridden=overridden, override_reason=payload.override_reason if overridden else None,
        issue_date=issue, due_date=issue + timedelta(days=agreement.payment_terms_days),
        status=InvoiceStatus.sent, created_by_id=current_user.id,
    )
    db.add(inv)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Invoice number clash, please try again")
    log_activity(db, current_user, ActivityType.create, f"Invoice {inv.invoice_number} raised ({total:,.2f})",
                 "invoice", inv.id, changes={
                     "amount": amount, "mou_amount": p.fee_amount, "overridden": overridden,
                     "override_reason": inv.override_reason, "agreement_id": agreement.id}, request=request)
    owners = [r[0] for r in (await db.execute(select(User.id).where(User.role == UserRole.owner))).all()]
    notify(db, owners, f"Invoice {inv.invoice_number} raised", f"INR {total:,.2f} due {inv.due_date:%d %b %Y}",
           NotifType.invoice, "/invoices", exclude=current_user.id)
    await db.commit()
    await db.refresh(inv)

    company = await db.get(Company, p.company_id)
    cand = await db.get(Candidate, p.candidate_id)
    contact = (await db.execute(select(Contact).where(Contact.company_id == p.company_id, Contact.email.isnot(None))
                                .order_by(Contact.is_primary.desc(), Contact.id))).scalars().first()
    if contact:
        from app.services.email import send_client_invoice_email
        await queue_email(send_client_invoice_email, contact.email, contact.name, inv.invoice_number,
                          cand.name if cand else "", inv.total_amount, inv.due_date)
    return _serialize(inv, company.name if company else None, cand.name if cand else None)


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(require_owner_or_bdm)):
    inv = await _get(db, invoice_id)
    company = await db.get(Company, inv.company_id)
    p = await db.get(Placement, inv.placement_id)
    cand = await db.get(Candidate, p.candidate_id) if p else None
    return _serialize(inv, company.name if company else None, cand.name if cand else None)


@router.post("/{invoice_id}/mark-paid")
async def mark_paid(invoice_id: int, request: Request, paid_on: Optional[datetime] = None,
                    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_owner)):
    inv = await _get(db, invoice_id)
    if inv.status != InvoiceStatus.sent:
        raise HTTPException(409, f"An invoice that is {inv.status.value} cannot be marked paid")
    inv.status = InvoiceStatus.paid
    inv.paid_on = paid_on or datetime.now(timezone.utc)
    p = await db.get(Placement, inv.placement_id)
    created = await billing.create_incentives(db, inv, p)
    log_activity(db, current_user, ActivityType.payment, f"Invoice {inv.invoice_number} marked paid",
                 "invoice", inv.id, changes={"incentives_created": len(created)}, request=request)
    for inc in created:
        notify(db, [inc.user_id], "Incentive earned", f"INR {inc.amount:,.2f} on invoice {inv.invoice_number}",
               NotifType.incentive, "/incentives", exclude=current_user.id)
    await db.commit()
    return _serialize(inv)


@router.post("/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: int, payload: CancelRequest, request: Request,
                         db: AsyncSession = Depends(get_db), current_user: User = Depends(require_owner)):
    inv = await _get(db, invoice_id)
    if inv.status == InvoiceStatus.cancelled:
        return _serialize(inv)
    old = inv.status
    inv.status = InvoiceStatus.cancelled
    voided = await billing.void_incentives(db, f"Invoice cancelled: {payload.reason}", invoice_id=inv.id)
    log_activity(db, current_user, ActivityType.update, f"Invoice {inv.invoice_number} cancelled",
                 "invoice", inv.id, changes={"status": {"from": old.value, "to": "cancelled"},
                                             "reason": payload.reason, "incentives_voided": voided},
                 request=request)
    # A corrected invoice can now be raised for the same placement
    await db.commit()
    return _serialize(inv)
