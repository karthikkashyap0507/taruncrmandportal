from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner_or_bdm
from app.models import (
    Lead, LeadNote, FollowUp, User,
    LeadStatus, LeadTemperature, ActivityLog, ActivityType,
)

router = APIRouter(prefix="/leads", tags=["leads"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    company_name: str
    contact_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_designation: Optional[str] = None
    source: Optional[str] = None
    status: LeadStatus = LeadStatus.new
    temperature: LeadTemperature = LeadTemperature.cold
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[float] = None
    expected_positions: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_to_id: Optional[int] = None


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_designation: Optional[str] = None
    source: Optional[str] = None
    status: Optional[LeadStatus] = None
    temperature: Optional[LeadTemperature] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[float] = None
    expected_positions: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_to_id: Optional[int] = None
    converted: Optional[bool] = None
    converted_at: Optional[datetime] = None


class NoteCreate(BaseModel):
    content: str


class FollowUpCreate(BaseModel):
    scheduled_at: datetime
    type: Optional[str] = "call"
    notes: Optional[str] = None


def _serialize_lead(lead: Lead, include_notes: bool = False) -> dict:
    data = {
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
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_leads(
    status: Optional[str] = None,
    temperature: Optional[str] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = Query(None),
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Lead)

    # HR can only see their assigned leads, BDM/Owner see all
    from app.models import UserRole
    if current_user.role == UserRole.hr:
        query = query.where(Lead.assigned_to_id == current_user.id)

    if status:
        query = query.where(Lead.status == status)
    if temperature:
        query = query.where(Lead.temperature == temperature)
    if assigned_to:
        query = query.where(Lead.assigned_to_id == assigned_to)
    if search:
        query = query.where(
            or_(
                Lead.company_name.ilike(f"%{search}%"),
                Lead.contact_name.ilike(f"%{search}%"),
                Lead.contact_email.ilike(f"%{search}%"),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.order_by(Lead.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [_serialize_lead(l) for l in leads],
    }


@router.get("/pipeline")
async def get_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Kanban pipeline grouped by status."""
    from app.models import UserRole
    query = select(Lead)
    if current_user.role == UserRole.hr:
        query = query.where(Lead.assigned_to_id == current_user.id)

    result = await db.execute(query)
    leads = result.scalars().all()

    pipeline = {}
    for status in LeadStatus:
        pipeline[status.value] = [_serialize_lead(l) for l in leads if l.status == status]

    return pipeline


@router.post("/", status_code=201)
async def create_lead(
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = Lead(
        **payload.model_dump(exclude_none=True),
        created_by_id=current_user.id,
    )
    if not lead.assigned_to_id:
        lead.assigned_to_id = current_user.id
    db.add(lead)
    log = ActivityLog(
        user_id=current_user.id,
        action=ActivityType.create,
        description=f"Created lead: {payload.company_name}",
        entity_type="lead",
    )
    db.add(log)
    await db.commit()
    await db.refresh(lead)
    return _serialize_lead(lead)


@router.get("/{lead_id}")
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return _serialize_lead(lead, include_notes=True)


@router.put("/{lead_id}")
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    old_status = lead.status
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(lead, field, val)
    lead.updated_at = datetime.now(timezone.utc)

    if payload.status and payload.status != old_status:
        log = ActivityLog(
            user_id=current_user.id,
            action=ActivityType.status_change,
            description=f"Lead {lead.company_name}: {old_status.value} → {payload.status.value}",
            entity_type="lead",
            entity_id=lead_id,
        )
        db.add(log)

    await db.commit()
    return _serialize_lead(lead)


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status: LeadStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.status = status
    lead.updated_at = datetime.now(timezone.utc)
    if status == LeadStatus.converted and not lead.converted:
        lead.converted = True
        lead.converted_at = datetime.now(timezone.utc)
    await db.commit()
    return _serialize_lead(lead)


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"message": "Lead deleted"}


@router.get("/{lead_id}/notes")
async def get_notes(lead_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
    )
    notes = result.scalars().all()
    return [{"id": n.id, "content": n.content, "created_by_id": n.created_by_id, "created_at": n.created_at.isoformat()} for n in notes]


@router.post("/{lead_id}/notes", status_code=201)
async def add_note(lead_id: int, payload: NoteCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    note = LeadNote(lead_id=lead_id, content=payload.content, created_by_id=current_user.id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return {"id": note.id, "content": note.content, "created_at": note.created_at.isoformat()}


@router.get("/{lead_id}/followups")
async def get_followups(lead_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.scheduled_at.asc())
    )
    fups = result.scalars().all()
    return [{"id": f.id, "type": f.type, "scheduled_at": f.scheduled_at.isoformat(), "completed": f.completed, "notes": f.notes} for f in fups]


@router.post("/{lead_id}/followups", status_code=201)
async def add_followup(lead_id: int, payload: FollowUpCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    fup = FollowUp(lead_id=lead_id, type=payload.type, scheduled_at=payload.scheduled_at, notes=payload.notes, created_by_id=current_user.id)
    db.add(fup)
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
    result = await db.execute(select(FollowUp).where(FollowUp.id == fup_id, FollowUp.lead_id == lead_id))
    fup = result.scalar_one_or_none()
    if not fup:
        raise HTTPException(404, "Follow-up not found")
    fup.completed = True
    fup.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Marked as completed"}
