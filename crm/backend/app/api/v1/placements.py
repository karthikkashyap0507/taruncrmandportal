"""Placements: a candidate placed with a client under an MOU, through to joining."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import utc
from app.models import (
    ActivityType, Agreement, Candidate, Company, Contact, CRMJob, Invoice, InvoiceStatus, NotifType, Placement, PlacementStatus, User,
    UserRole,
)
from app.services import billing
from app.services.activity import diff, log_activity, notify, queue_email

router = APIRouter(prefix="/placements", tags=["placements"])


class PlacementCreate(BaseModel):
    candidate_id: int
    job_id: int
    offered_ctc: float = Field(..., gt=0, le=1_000_000_000)
    offer_date: Optional[datetime] = None
    expected_joining_date: Optional[datetime] = None
    recruiter_id: Optional[int] = None
    bdm_id: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class PlacementUpdate(BaseModel):
    offered_ctc: Optional[float] = Field(default=None, gt=0, le=1_000_000_000)
    expected_joining_date: Optional[datetime] = None
    recruiter_id: Optional[int] = None
    bdm_id: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class StatusChange(BaseModel):
    status: PlacementStatus
    date: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=2000)


def _serialize(p: Placement, names: dict | None = None) -> dict:
    names = names or {}
    return {
        "id": p.id,
        "candidate_id": p.candidate_id,
        "candidate_name": names.get("candidate"),
        "job_id": p.job_id,
        "job_title": names.get("job"),
        "company_id": p.company_id,
        "company_name": names.get("company"),
        "agreement_id": p.agreement_id,
        "recruiter_id": p.recruiter_id,
        "bdm_id": p.bdm_id,
        "offered_ctc": p.offered_ctc,
        "offer_date": p.offer_date.isoformat() if p.offer_date else None,
        "expected_joining_date": p.expected_joining_date.isoformat() if p.expected_joining_date else None,
        "joined_on": p.joined_on.isoformat() if p.joined_on else None,
        "left_on": p.left_on.isoformat() if p.left_on else None,
        "status": p.status.value,
        "fee_type": p.fee_type.value,
        "fee_value": p.fee_value,
        "fee_amount": p.fee_amount,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _visible(q, user: User):
    """Owners and BDMs see every placement; HR sees placements they are credited on."""
    if user.role == UserRole.hr:
        return q.where(Placement.recruiter_id == user.id)
    return q


async def _get(db: AsyncSession, placement_id: int, user: User) -> Placement:
    p = (await db.execute(_visible(select(Placement).where(Placement.id == placement_id), user))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Placement not found")
    return p


async def _names(db: AsyncSession, p: Placement) -> dict:
    cand, job, comp = await db.get(Candidate, p.candidate_id), await db.get(CRMJob, p.job_id), \
        await db.get(Company, p.company_id)
    return {"candidate": cand.name if cand else None, "job": job.title if job else None,
            "company": comp.name if comp else None}


async def _check_user(db: AsyncSession, user_id: Optional[int], label: str) -> None:
    if user_id is None:
        return
    u = await db.get(User, user_id)
    if not u or not u.is_active:
        raise HTTPException(400, f"The selected {label} doesn't exist or is inactive")


async def _staff(db: AsyncSession, roles) -> list[int]:
    return [r[0] for r in (await db.execute(
        select(User.id).where(User.role.in_(roles), User.is_active == True))).all()]  # noqa: E712


@router.get("/")
async def list_placements(
    status: Optional[PlacementStatus] = None,
    company_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _visible(select(Placement, Candidate.name, CRMJob.title, Company.name)
                 .join(Candidate, Candidate.id == Placement.candidate_id)
                 .join(CRMJob, CRMJob.id == Placement.job_id)
                 .join(Company, Company.id == Placement.company_id), current_user)
    if status:
        q = q.where(Placement.status == status)
    if company_id:
        q = q.where(Placement.company_id == company_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(Placement.id.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {"total": total, "page": page, "limit": limit,
            "data": [_serialize(p, {"candidate": c, "job": j, "company": co}) for p, c, j, co in rows]}


@router.post("/", status_code=201)
async def create_placement(payload: PlacementCreate, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    cand = await db.get(Candidate, payload.candidate_id)
    if not cand:
        raise HTTPException(404, "Candidate not found")
    job = await db.get(CRMJob, payload.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.company_id:
        raise HTTPException(409, "Link this job to a client first: a placement is billed to the job's client")
    existing = (await db.execute(select(Placement).where(
        Placement.candidate_id == cand.id, Placement.job_id == job.id))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"{cand.name} already has a placement for this job (#{existing.id})")

    offer_date = payload.offer_date or datetime.now(timezone.utc)
    agreement = await billing.active_agreement_for(db, job.company_id, offer_date)
    if not agreement:
        company = await db.get(Company, job.company_id)
        raise HTTPException(409, f"There is no active MOU with {company.name if company else 'this client'} "
                                 "covering the offer date. Activate an MOU before recording the placement.")

    recruiter_id = payload.recruiter_id
    if current_user.role == UserRole.hr:
        recruiter_id = current_user.id   # HR can only credit themselves
    elif recruiter_id is None:
        recruiter_id = cand.created_by_id
    await _check_user(db, recruiter_id, "recruiter")
    await _check_user(db, payload.bdm_id, "BDM")

    p = Placement(
        candidate_id=cand.id, job_id=job.id, company_id=job.company_id, agreement_id=agreement.id,
        recruiter_id=recruiter_id, bdm_id=payload.bdm_id, offered_ctc=payload.offered_ctc,
        offer_date=offer_date, expected_joining_date=payload.expected_joining_date,
        status=PlacementStatus.offered, notes=payload.notes,
        # Fee terms are copied from the MOU now, so later MOU edits never change this placement
        fee_type=agreement.fee_type, fee_value=agreement.fee_value,
        fee_amount=billing.compute_fee(agreement.fee_type, agreement.fee_value, payload.offered_ctc),
        created_by_id=current_user.id,
    )
    db.add(p)
    await db.flush()
    log_activity(db, current_user, ActivityType.create,
                 f"Placement recorded: {cand.name} at {job.title} (fee {p.fee_amount:,.2f})", "placement", p.id,
                 changes={"offered_ctc": p.offered_ctc, "fee_type": p.fee_type.value, "fee_value": p.fee_value,
                          "fee_amount": p.fee_amount, "agreement_id": agreement.id}, request=request)
    notify(db, [*await _staff(db, (UserRole.owner,)), p.bdm_id, p.recruiter_id],
           f"Offer recorded: {cand.name}", f"{job.title} - expected joining "
           f"{p.expected_joining_date:%d %b %Y}" if p.expected_joining_date else f"{job.title}",
           NotifType.placement, "/placements", exclude=current_user.id)
    await db.commit()
    await db.refresh(p)
    return _serialize(p, await _names(db, p))


@router.get("/{placement_id}")
async def get_placement(placement_id: int, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    p = await _get(db, placement_id, current_user)
    data = _serialize(p, await _names(db, p))
    inv = (await db.execute(select(Invoice).where(Invoice.placement_id == p.id)
                            .order_by(Invoice.id.desc()))).scalars().first()
    data["invoice"] = ({"id": inv.id, "invoice_number": inv.invoice_number, "status": inv.status.value,
                        "total_amount": inv.total_amount} if inv else None)
    return data


@router.put("/{placement_id}")
async def update_placement(placement_id: int, payload: PlacementUpdate, request: Request,
                           db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = await _get(db, placement_id, current_user)
    if (await db.execute(select(Invoice.id).where(Invoice.placement_id == p.id,
                                                  Invoice.status != InvoiceStatus.cancelled))).first():
        raise HTTPException(409, "This placement has been invoiced and is locked. Cancel the invoice to change it.")
    data = payload.model_dump(exclude_none=True)
    if current_user.role == UserRole.hr:
        if "recruiter_id" in data or "bdm_id" in data:
            raise HTTPException(403, "Only owners and BDMs can change who is credited for a placement")
    await _check_user(db, data.get("recruiter_id"), "recruiter")
    await _check_user(db, data.get("bdm_id"), "BDM")
    changes = diff(p, data)
    for k, v in data.items():
        setattr(p, k, v)
    if "offered_ctc" in data:
        p.fee_amount = billing.compute_fee(p.fee_type, p.fee_value, p.offered_ctc)
        changes["fee_amount"] = p.fee_amount
    p.updated_at = datetime.now(timezone.utc)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated placement #{p.id}", "placement", p.id,
                     changes=changes, request=request)
    await db.commit()
    return _serialize(p, await _names(db, p))


@router.post("/{placement_id}/status")
async def change_status(placement_id: int, payload: StatusChange, request: Request,
                        db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = await _get(db, placement_id, current_user)
    allowed = {
        PlacementStatus.offered: {PlacementStatus.joined, PlacementStatus.dropped},
        PlacementStatus.joined: {PlacementStatus.left_in_guarantee},
    }
    if payload.status not in allowed.get(p.status, set()):
        raise HTTPException(409, f"A placement that is {p.status.value} cannot be marked {payload.status.value}")
    when = payload.date or datetime.now(timezone.utc)
    names = await _names(db, p)
    old = p.status

    if payload.status == PlacementStatus.left_in_guarantee:
        agr = await db.get(Agreement, p.agreement_id)
        limit = utc(p.joined_on) + timedelta(days=agr.replacement_guarantee_days if agr else 0)
        if utc(when) > limit:
            raise HTTPException(409, "The replacement guarantee period has already ended for this placement")
        p.left_on = when
        voided = await billing.void_incentives(db, "Candidate left within the guarantee period",
                                               placement_id=p.id)
        notify(db, [*await _staff(db, (UserRole.owner, UserRole.bdm)), p.recruiter_id],
               f"{names['candidate']} left within guarantee",
               f"{names['company']} - a replacement is owed; {voided} incentive(s) voided",
               NotifType.placement, "/placements", exclude=current_user.id)
    elif payload.status == PlacementStatus.joined:
        p.joined_on = when
        notify(db, [*await _staff(db, (UserRole.owner,)), p.bdm_id, p.recruiter_id],
               f"{names['candidate']} joined {names['company']}", f"{names['job']} - ready to invoice",
               NotifType.joining, "/placements", exclude=current_user.id)
    else:
        notify(db, [*await _staff(db, (UserRole.owner,)), p.bdm_id, p.recruiter_id],
               f"{names['candidate']} did not join", f"{names['company']} - {names['job']}",
               NotifType.placement, "/placements", exclude=current_user.id)

    p.status = payload.status
    p.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.status_change,
                 f"Placement #{p.id} ({names['candidate']}): {old.value} -> {payload.status.value}",
                 "placement", p.id, changes={"status": {"from": old.value, "to": payload.status.value},
                                             "date": when.isoformat(), "note": payload.note}, request=request)
    await db.commit()

    if payload.status == PlacementStatus.joined:
        from app.services.email import send_client_joining_email, send_joining_confirmation_email
        cand = await db.get(Candidate, p.candidate_id)
        if cand and cand.email:
            await queue_email(send_joining_confirmation_email, cand.email, cand.name, names["company"],
                              names["job"], when)
        contact = (await db.execute(select(Contact).where(Contact.company_id == p.company_id, Contact.email.isnot(None))
                                    .order_by(Contact.is_primary.desc(), Contact.id))).scalars().first()
        if contact:
            await queue_email(send_client_joining_email, contact.email, contact.name, names["candidate"],
                              names["job"], when)
    return _serialize(p, names)
