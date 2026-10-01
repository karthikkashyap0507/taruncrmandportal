"""Client agreements (MOUs): the fee terms placements and invoices are billed on."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import is_owner, require_owner, require_owner_or_bdm
from app.core.files import save_document, sign_url
from app.models import ActivityType, Agreement, AgreementStatus, Company, FeeType, Placement, User
from app.services.activity import diff, log_activity

router = APIRouter(prefix="/agreements", tags=["agreements"])

FINANCIAL_FIELDS = {"fee_type", "fee_value", "payment_terms_days", "replacement_guarantee_days", "start_date",
                    "end_date"}


class AgreementBase(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    fee_type: Optional[FeeType] = None
    fee_value: Optional[float] = Field(default=None, gt=0)
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=365)
    replacement_guarantee_days: Optional[int] = Field(default=None, ge=0, le=365)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def check_terms(self):
        if self.fee_type == FeeType.percentage and self.fee_value is not None and self.fee_value > 100:
            raise ValueError("A percentage fee cannot be more than 100%")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after the start date")
        return self


class AgreementCreate(AgreementBase):
    company_id: int
    title: str = Field(..., min_length=2, max_length=255)
    fee_type: FeeType = FeeType.percentage
    fee_value: float = Field(..., gt=0)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    replacement_guarantee_days: int = Field(default=90, ge=0, le=365)
    start_date: datetime


class AgreementUpdate(AgreementBase):
    pass


def _serialize(a: Agreement, company_name: str | None = None) -> dict:
    return {
        "id": a.id,
        "company_id": a.company_id,
        "company_name": company_name,
        "title": a.title,
        "fee_type": a.fee_type.value,
        "fee_value": a.fee_value,
        "payment_terms_days": a.payment_terms_days,
        "replacement_guarantee_days": a.replacement_guarantee_days,
        "start_date": a.start_date.isoformat() if a.start_date else None,
        "end_date": a.end_date.isoformat() if a.end_date else None,
        "status": a.status.value,
        "document_url": sign_url(a.document_url),
        "notes": a.notes,
        "created_by_id": a.created_by_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


async def _get(db: AsyncSession, agreement_id: int) -> Agreement:
    a = await db.get(Agreement, agreement_id)
    if not a:
        raise HTTPException(404, "Agreement not found")
    return a


@router.get("/")
async def list_agreements(
    company_id: Optional[int] = None,
    status: Optional[AgreementStatus] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    q = select(Agreement, Company.name).join(Company, Company.id == Agreement.company_id)
    if company_id:
        q = q.where(Agreement.company_id == company_id)
    if status:
        q = q.where(Agreement.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(Agreement.id.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize(a, n) for a, n in rows]}


@router.post("/", status_code=201)
async def create_agreement(payload: AgreementCreate, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_owner_or_bdm)):
    company = await db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(404, "Client not found")
    a = Agreement(**payload.model_dump(exclude_none=True), status=AgreementStatus.draft,
                  created_by_id=current_user.id)
    db.add(a)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Created MOU '{a.title}' for {company.name}",
                 "agreement", a.id, changes={k: v for k, v in diff(Agreement(), payload.model_dump()).items()},
                 request=request)
    await db.commit()
    await db.refresh(a)
    return _serialize(a, company.name)


@router.get("/{agreement_id}")
async def get_agreement(agreement_id: int, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(require_owner_or_bdm)):
    a = await _get(db, agreement_id)
    company = await db.get(Company, a.company_id)
    data = _serialize(a, company.name if company else None)
    data["placements"] = (await db.execute(
        select(func.count()).select_from(Placement).where(Placement.agreement_id == a.id))).scalar()
    return data


@router.put("/{agreement_id}")
async def update_agreement(agreement_id: int, payload: AgreementUpdate, request: Request,
                           db: AsyncSession = Depends(get_db), current_user: User = Depends(require_owner_or_bdm)):
    a = await _get(db, agreement_id)
    data = payload.model_dump(exclude_none=True)
    if a.status != AgreementStatus.draft and FINANCIAL_FIELDS & data.keys() and not is_owner(current_user):
        raise HTTPException(403, "Only the owner can change the terms of an active or closed MOU")
    fee_type = data.get("fee_type", a.fee_type)
    fee_value = data.get("fee_value", a.fee_value)
    if fee_type == FeeType.percentage and fee_value > 100:
        raise HTTPException(422, "A percentage fee cannot be more than 100%")
    changes = diff(a, data)
    for k, v in data.items():
        setattr(a, k, v)
    a.updated_at = datetime.now(timezone.utc)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated MOU '{a.title}'", "agreement", a.id,
                     changes=changes, request=request)
    await db.commit()
    return _serialize(a)


@router.post("/{agreement_id}/status")
async def set_status(agreement_id: int, status: AgreementStatus, request: Request,
                     db: AsyncSession = Depends(get_db), current_user: User = Depends(require_owner)):
    """Activate / terminate / expire an MOU (owner only)."""
    a = await _get(db, agreement_id)
    if a.status == status:
        return _serialize(a)
    if status == AgreementStatus.draft:
        raise HTTPException(409, "An MOU cannot be moved back to draft")
    old = a.status
    a.status = status
    a.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.approve, f"MOU '{a.title}': {old.value} -> {status.value}",
                 "agreement", a.id, changes={"status": {"from": old.value, "to": status.value}}, request=request)
    await db.commit()
    return _serialize(a)


@router.post("/{agreement_id}/document")
async def upload_document(agreement_id: int, request: Request, file: UploadFile = File(...),
                          db: AsyncSession = Depends(get_db), current_user: User = Depends(require_owner_or_bdm)):
    a = await _get(db, agreement_id)
    a.document_url = await save_document(file, "agreements", f"mou{agreement_id}")
    a.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.file_upload, f"Uploaded signed MOU for '{a.title}'",
                 "agreement", a.id, request=request)
    await db.commit()
    return {"document_url": sign_url(a.document_url)}
