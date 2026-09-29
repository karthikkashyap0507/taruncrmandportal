from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Company, Contact, User, Lead

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
    page: int = 1,
    limit: int = 20,
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = Company(**payload.model_dump(exclude_none=True))
    db.add(company)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Client not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(company, field, val)
    await db.commit()
    return _serialize_company(company)


@router.delete("/{company_id}")
async def delete_client(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Client not found")
    await db.delete(company)
    await db.commit()
    return {"message": "Client deleted"}


@router.post("/{company_id}/contacts", status_code=201)
async def add_contact(
    company_id: int,
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = Contact(**payload.model_dump(exclude_none=True))
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return _serialize_contact(contact)


@router.put("/contacts/{contact_id}")
async def update_contact(
    contact_id: int,
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(contact, field, val)
    await db.commit()
    return _serialize_contact(contact)


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    await db.delete(contact)
    await db.commit()
    return {"message": "Contact deleted"}
