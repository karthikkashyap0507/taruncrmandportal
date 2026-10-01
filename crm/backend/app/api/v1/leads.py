from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner_or_bdm
from app.models import (
    ActivityType, FollowUp, Lead, LeadNote, LeadStatus, LeadTemperature, NotifType, User, UserRole,
)
from app.services.activity import diff, email_users, log_activity, notify, queue_email

router = APIRouter(prefix="/leads", tags=["leads"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str = Field(..., min_length=1, max_length=120)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    contact_designation: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=100)
    status: LeadStatus = LeadStatus.new
    temperature: LeadTemperature = LeadTemperature.cold
    industry: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    requirement: Optional[str] = Field(default=None, max_length=10000)
    budget: Optional[float] = Field(default=None, ge=0)
    expected_positions: Optional[int] = Field(default=None, ge=0, le=100000)
    notes: Optional[str] = Field(default=None, max_length=10000)
    tags: Optional[List[str]] = None
    assigned_to_id: Optional[int] = None


class LeadUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    contact_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    contact_designation: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=100)
    status: Optional[LeadStatus] = None
    temperature: Optional[LeadTemperature] = None
    industry: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    requirement: Optional[str] = Field(default=None, max_length=10000)
    budget: Optional[float] = Field(default=None, ge=0)
    expected_positions: Optional[int] = Field(default=None, ge=0, le=100000)
    notes: Optional[str] = Field(default=None, max_length=10000)
    tags: Optional[List[str]] = None
    assigned_to_id: Optional[int] = None


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class FollowUpCreate(BaseModel):
    scheduled_at: datetime
    type: Optional[str] = Field(default="call", max_length=50)
    notes: Optional[str] = Field(default=None, max_length=5000)


def _serialize_lead(lead: Lead, include_notes: bool = False) -> dict:
    return {
        "id": lead.id,
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "contact_phone": lead.contact_phone,
        "contact_designation": lead.contact_designation,
        "source": lead.source,
        "status": lead.status.value,
        "temperature": lead.temperature.value,
        "industry": lead.industry,
        "location": lead.location,
        "website": lead.website,
        "requirement": lead.requirement,
        "budget": lead.budget,
        "expected_positions": lead.expected_positions,
        "notes": lead.notes,
        "tags": lead.tags or [],
        "converted": lead.converted,
        "converted_at": lead.converted_at.isoformat() if lead.converted_at else None,
        "assigned_to_id": lead.assigned_to_id,
        "created_by_id": lead.created_by_id,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


def _visible(query, user: User):
    """HR users only see leads assigned to them; owners and BDMs see all leads."""
    if user.role == UserRole.hr:
        return query.where(Lead.assigned_to_id == user.id)
    return query


async def _get_lead(db: AsyncSession, lead_id: int, user: User) -> Lead:
    lead = (await db.execute(_visible(select(Lead).where(Lead.id == lead_id), user))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


async def _owner_ids(db: AsyncSession) -> list[int]:
    rows = await db.execute(select(User.id).where(User.role == UserRole.owner, User.is_active == True))  # noqa: E712
    return [r[0] for r in rows.all()]


async def _check_assignee(db: AsyncSession, user_id: Optional[int]) -> None:
    if user_id is None:
        return
    target = await db.get(User, user_id)
    if not target or not target.is_active:
        raise HTTPException(400, "The selected team member doesn't exist or is inactive")


async def _notify_assigned(db: AsyncSession, lead: Lead, actor: User) -> None:
    """Call after commit: tell the new assignee (in-app was added before commit)."""
    if lead.assigned_to_id and lead.assigned_to_id != actor.id:
        assignee = await db.get(User, lead.assigned_to_id)
        if assignee:
            from app.services.email import send_lead_assigned_email
            await queue_email(send_lead_assigned_email, assignee.email, assignee.name, lead.company_name, lead.id)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_leads(
    status: Optional[str] = None,
    temperature: Optional[str] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _visible(select(Lead), current_user)
    if status:
        query = query.where(Lead.status == status)
    if temperature:
        query = query.where(Lead.temperature == temperature)
    if assigned_to:
        query = query.where(Lead.assigned_to_id == assigned_to)
    if search:
        query = query.where(or_(
            Lead.company_name.ilike(f"%{search}%"),
            Lead.contact_name.ilike(f"%{search}%"),
            Lead.contact_email.ilike(f"%{search}%"),
        ))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Lead.created_at.desc()).offset((page - 1) * limit).limit(limit)
    leads = (await db.execute(query)).scalars().all()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize_lead(l) for l in leads]}


@router.get("/pipeline")
async def get_pipeline(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Kanban pipeline grouped by status."""
    leads = (await db.execute(_visible(select(Lead), current_user).order_by(Lead.created_at.desc()).limit(2000))).scalars().all()
    pipeline = {s.value: [] for s in LeadStatus}
    for lead in leads:
        pipeline[lead.status.value].append(_serialize_lead(lead))
    return pipeline


@router.post("/", status_code=201)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_none=True)
    if current_user.role == UserRole.hr:
        data["assigned_to_id"] = current_user.id  # HR can only create leads for themselves
    await _check_assignee(db, data.get("assigned_to_id"))
    lead = Lead(**data, created_by_id=current_user.id)
    if not lead.assigned_to_id:
        lead.assigned_to_id = current_user.id
    db.add(lead)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Created lead: {lead.company_name}", "lead", lead.id,
                 request=request)
    notify(db, [lead.assigned_to_id], "New lead assigned to you", f"{lead.company_name} ({lead.contact_name})",
           NotifType.lead_assigned, f"/leads/{lead.id}", exclude=current_user.id)
    await db.commit()
    await db.refresh(lead)
    await _notify_assigned(db, lead, current_user)
    return _serialize_lead(lead)


@router.get("/{lead_id}")
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _serialize_lead(await _get_lead(db, lead_id, current_user), include_notes=True)


async def _apply_status(db: AsyncSession, lead: Lead, new_status: LeadStatus, actor: User, request: Request) -> None:
    old = lead.status
    lead.status = new_status
    if new_status == LeadStatus.converted and not lead.converted:
        lead.converted = True
        lead.converted_at = datetime.now(timezone.utc)
    log_activity(db, actor, ActivityType.status_change,
                 f"Lead {lead.company_name}: {old.value} -> {new_status.value}", "lead", lead.id,
                 changes={"status": {"from": old.value, "to": new_status.value}}, request=request)
    notify(db, [lead.assigned_to_id, *await _owner_ids(db)], f"Lead moved to {new_status.value}",
           f"{lead.company_name}: {old.value} -> {new_status.value}", NotifType.status_changed,
           f"/leads/{lead.id}", exclude=actor.id)


@router.put("/{lead_id}")
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = await _get_lead(db, lead_id, current_user)
    data = payload.model_dump(exclude_none=True)
    if "assigned_to_id" in data and data["assigned_to_id"] != lead.assigned_to_id:
        if current_user.role == UserRole.hr:
            raise HTTPException(403, "Only owners and BDMs can reassign leads")
        await _check_assignee(db, data["assigned_to_id"])
    new_status = data.pop("status", None)
    changes = diff(lead, data)
    reassigned = "assigned_to_id" in changes
    for field, val in data.items():
        setattr(lead, field, val)
    lead.updated_at = datetime.now(timezone.utc)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated lead: {lead.company_name}", "lead", lead.id,
                     changes=changes, request=request)
    if new_status and new_status != lead.status:
        await _apply_status(db, lead, new_status, current_user, request)
    if reassigned:
        notify(db, [lead.assigned_to_id], "Lead assigned to you", lead.company_name, NotifType.lead_assigned,
               f"/leads/{lead.id}", exclude=current_user.id)
    await db.commit()
    if reassigned:
        await _notify_assigned(db, lead, current_user)
    return _serialize_lead(lead)


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status: LeadStatus,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = await _get_lead(db, lead_id, current_user)
    if status != lead.status:
        await _apply_status(db, lead, status, current_user, request)
        lead.updated_at = datetime.now(timezone.utc)
        await db.commit()
    return _serialize_lead(lead)


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    lead = await _get_lead(db, lead_id, current_user)
    log_activity(db, current_user, ActivityType.delete, f"Deleted lead: {lead.company_name}", "lead", lead.id,
                 request=request)
    await db.delete(lead)
    await db.commit()
    return {"message": "Lead deleted"}


@router.get("/{lead_id}/notes")
async def get_notes(lead_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _get_lead(db, lead_id, current_user)
    notes = (await db.execute(
        select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
    )).scalars().all()
    return [{"id": n.id, "content": n.content, "created_by_id": n.created_by_id,
             "created_at": n.created_at.isoformat()} for n in notes]


@router.post("/{lead_id}/notes", status_code=201)
async def add_note(lead_id: int, payload: NoteCreate, request: Request, db: AsyncSession = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    lead = await _get_lead(db, lead_id, current_user)
    note = LeadNote(lead_id=lead_id, content=payload.content, created_by_id=current_user.id)
    db.add(note)
    log_activity(db, current_user, ActivityType.note_added, f"Note on lead {lead.company_name}", "lead", lead.id,
                 request=request)
    await db.commit()
    await db.refresh(note)
    return {"id": note.id, "content": note.content, "created_at": note.created_at.isoformat()}


@router.get("/{lead_id}/followups")
async def get_followups(lead_id: int, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    await _get_lead(db, lead_id, current_user)
    fups = (await db.execute(
        select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.scheduled_at.asc())
    )).scalars().all()
    return [{"id": f.id, "type": f.type, "scheduled_at": f.scheduled_at.isoformat(), "completed": f.completed,
             "notes": f.notes} for f in fups]


@router.post("/{lead_id}/followups", status_code=201)
async def add_followup(lead_id: int, payload: FollowUpCreate, request: Request, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    lead = await _get_lead(db, lead_id, current_user)
    fup = FollowUp(lead_id=lead_id, type=payload.type, scheduled_at=payload.scheduled_at, notes=payload.notes,
                   created_by_id=current_user.id)
    db.add(fup)
    log_activity(db, current_user, ActivityType.create, f"Follow-up scheduled for {lead.company_name}", "lead",
                 lead.id, request=request)
    await db.commit()
    await db.refresh(fup)
    return {"id": fup.id, "scheduled_at": fup.scheduled_at.isoformat(), "type": fup.type}


@router.patch("/{lead_id}/followups/{fup_id}/complete")
async def complete_followup(
    lead_id: int,
    fup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_lead(db, lead_id, current_user)
    fup = (await db.execute(select(FollowUp).where(FollowUp.id == fup_id, FollowUp.lead_id == lead_id))).scalar_one_or_none()
    if not fup:
        raise HTTPException(404, "Follow-up not found")
    fup.completed = True
    fup.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Marked as completed"}
