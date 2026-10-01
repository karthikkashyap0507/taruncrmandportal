from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner, require_owner_or_bdm
from app.models import ActivityType, Agreement, Company, Contact, CRMJob, Invoice, Lead, Placement, User
from app.services.activity import diff, log_activity

router = APIRouter(prefix="/clients", tags=["clients"])


class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    linkedin_url: Optional[str] = None
    lead_id: Optional[int] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    linkedin_url: Optional[str] = None


class ContactCreate(BaseModel):
    company_id: int
    name: str
    designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    is_primary: bool = False


def _serialize_company(c: Company) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "industry": c.industry,
        "website": c.website,
        "location": c.location,
        "size": c.size,
        "description": c.description,
        "linkedin_url": c.linkedin_url,
        "logo_url": c.logo_url,
        "created_at": c.created_at.isoformat(),
    }


def _serialize_contact(c: Contact) -> dict:
    return {
        "id": c.id,
        "company_id": c.company_id,
        "name": c.name,
        "designation": c.designation,
        "email": c.email,
        "phone": c.phone,
        "linkedin_url": c.linkedin_url,
        "is_primary": c.is_primary,
        "created_at": c.created_at.isoformat(),
    }


@router.get("/")
async def list_clients(
    search: Optional[str] = Query(None),
    industry: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Company)
    if search:
        query = query.where(or_(Company.name.ilike(f"%{search}%"), Company.industry.ilike(f"%{search}%")))
    if industry:
        query = query.where(Company.industry == industry)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    query = query.order_by(Company.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    companies = result.scalars().all()

    return {"total": total, "page": page, "limit": limit, "data": [_serialize_company(c) for c in companies]}


@router.post("/", status_code=201)
async def create_client(
    payload: CompanyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    company = Company(**payload.model_dump(exclude_none=True))
    db.add(company)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Added client {company.name}", "client", company.id,
                 request=request)
    await db.commit()
    await db.refresh(company)
    return _serialize_company(company)


@router.get("/{company_id}")
async def get_client(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Client not found")

    contacts_result = await db.execute(select(Contact).where(Contact.company_id == company_id))
    contacts = contacts_result.scalars().all()

    data = _serialize_company(company)
    data["contacts"] = [_serialize_contact(c) for c in contacts]
    return data


@router.put("/{company_id}")
async def update_client(
    company_id: int,
    payload: CompanyUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Client not found")
    data = payload.model_dump(exclude_none=True)
    changes = diff(company, data)
    for field, val in data.items():
        setattr(company, field, val)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated client {company.name}", "client",
                     company.id, changes=changes, request=request)
    await db.commit()
    return _serialize_company(company)


@router.delete("/{company_id}")
async def delete_client(
    company_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Client not found")
    for model, label in ((Agreement, "MOUs"), (Placement, "placements"), (Invoice, "invoices")):
        if (await db.execute(select(func.count()).select_from(model).where(model.company_id == company_id))).scalar():
            raise HTTPException(409, f"This client has {label} linked to billing and can't be deleted")
    await db.execute(update(CRMJob).where(CRMJob.company_id == company_id).values(company_id=None))
    log_activity(db, current_user, ActivityType.delete, f"Deleted client {company.name}", "client", company.id,
                 request=request)
    await db.delete(company)
    await db.commit()
    return {"message": "Client deleted"}


@router.post("/{company_id}/contacts", status_code=201)
async def add_contact(
    company_id: int,
    payload: ContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    if not await db.get(Company, company_id):
        raise HTTPException(404, "Client not found")
    data = payload.model_dump(exclude_none=True)
    data["company_id"] = company_id  # the URL decides which client the contact belongs to
    contact = Contact(**data)
    db.add(contact)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Added contact {contact.name}", "client", company_id,
                 request=request)
    await db.commit()
    await db.refresh(contact)
    return _serialize_contact(contact)


@router.put("/contacts/{contact_id}")
async def update_contact(
    contact_id: int,
    payload: ContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    data = payload.model_dump(exclude_none=True)
    data.pop("company_id", None)  # contacts can't be moved to another client
    changes = diff(contact, data)
    for field, val in data.items():
        setattr(contact, field, val)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated contact {contact.name}", "client",
                     contact.company_id, changes=changes, request=request)
    await db.commit()
    return _serialize_contact(contact)


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    log_activity(db, current_user, ActivityType.delete, f"Deleted contact {contact.name}", "client",
                 contact.company_id, request=request)
    await db.delete(contact)
    await db.commit()
    return {"message": "Contact deleted"}
