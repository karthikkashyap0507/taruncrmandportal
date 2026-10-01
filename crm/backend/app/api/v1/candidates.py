from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner
from app.core.files import save_document, sign_url
from app.core.ratelimit import upload_user_limiter
from app.models import (
    ActivityType, Application, ApplicationEvent, Candidate, CandidateNote, CandidateStatus, Interview,
    NotifType, Placement, User,
)
from app.services.activity import diff, log_activity, notify, queue_email
from app.services.dedupe import find_duplicates, normalize_email, normalize_phone

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Candidate is emailed when their status reaches one of these milestones
_EMAIL_ON_STATUS = {CandidateStatus.shortlisted, CandidateStatus.interviewing,
                    CandidateStatus.offered, CandidateStatus.placed}


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    skills: Optional[List[str]] = Field(default=None, max_length=100)
    experience_years: Optional[float] = Field(default=None, ge=0, le=60)
    current_title: Optional[str] = Field(default=None, max_length=255)
    current_company: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    expected_salary: Optional[str] = Field(default=None, max_length=100)
    notice_period: Optional[str] = Field(default=None, max_length=100)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    status: CandidateStatus = CandidateStatus.new
    source: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[List[str]] = None
    notes: Optional[str] = Field(default=None, max_length=10000)
    portal_candidate_id: Optional[int] = None


class CandidateUpdate(BaseModel):
    # ats_score is deliberately absent: it is only ever computed by the server
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    skills: Optional[List[str]] = Field(default=None, max_length=100)
    experience_years: Optional[float] = Field(default=None, ge=0, le=60)
    current_title: Optional[str] = Field(default=None, max_length=255)
    current_company: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    expected_salary: Optional[str] = Field(default=None, max_length=100)
    notice_period: Optional[str] = Field(default=None, max_length=100)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    status: Optional[CandidateStatus] = None
    source: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[List[str]] = None
    notes: Optional[str] = Field(default=None, max_length=10000)


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    type: Optional[str] = Field(default="general", max_length=50)


def _serialize(c: Candidate) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "skills": c.skills or [],
        "experience_years": c.experience_years,
        "current_title": c.current_title,
        "current_company": c.current_company,
        "location": c.location,
        "expected_salary": c.expected_salary,
        "notice_period": c.notice_period,
        "linkedin_url": c.linkedin_url,
        # Signed, expiring link (resumes are never publicly reachable)
        "resume_url": sign_url(c.resume_url),
        "status": c.status.value,
        "source": c.source,
        "tags": c.tags or [],
        "notes": c.notes,
        "ats_score": c.ats_score,
        "portal_candidate_id": c.portal_candidate_id,
        "created_by_id": c.created_by_id,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _compute_ats_score(candidate: Candidate, job_skills: List[str], required_exp: float) -> int:
    score = 0
    c_skills = [s.lower() for s in (candidate.skills or [])]
    j_skills = [s.lower() for s in job_skills]
    if j_skills:
        matched = sum(1 for s in j_skills if s in c_skills)
        score += int((matched / len(j_skills)) * 60)
    else:
        score += 30

    exp = candidate.experience_years or 0
    if required_exp <= 0:
        score += 20
    elif exp >= required_exp:
        score += 20
    elif exp >= required_exp * 0.75:
        score += 15
    elif exp >= required_exp * 0.5:
        score += 10
    else:
        score += 5

    keyword_fields = " ".join(filter(None, [candidate.current_title, candidate.notes, candidate.current_company]))
    if job_skills:
        kw_hits = sum(1 for s in j_skills if s in keyword_fields.lower())
        score += min(20, int((kw_hits / len(j_skills)) * 20))

    return min(100, score)


def _duplicate_error(dups: list[Candidate]) -> HTTPException:
    d = dups[0]
    return HTTPException(
        status_code=409,
        detail=f"A candidate with this email or phone already exists: {d.name} (#{d.id}). "
               "Open that profile instead, or ask the owner to merge the records.",
        headers={"X-Duplicate-Id": str(d.id)},
    )


async def _get(db: AsyncSession, candidate_id: int) -> Candidate:
    c = await db.get(Candidate, candidate_id)
    if not c:
        raise HTTPException(404, "Candidate not found")
    return c


@router.get("/")
async def list_candidates(
    status: Optional[str] = None,
    search: Optional[str] = Query(None, max_length=100),
    skill: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Candidate)
    if status:
        query = query.where(Candidate.status == status)
    if search:
        query = query.where(or_(
            Candidate.name.ilike(f"%{search}%"),
            Candidate.email.ilike(f"%{search}%"),
            Candidate.current_title.ilike(f"%{search}%"),
            Candidate.phone.ilike(f"%{search}%"),
        ))
    if skill:
        query = query.where(func.lower(Candidate.skills.cast(type_=Candidate.name.type)).like(f"%{skill.lower()}%"))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Candidate.created_at.desc()).offset((page - 1) * limit).limit(limit)
    candidates = (await db.execute(query)).scalars().all()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize(c) for c in candidates]}


@router.get("/duplicates/check")
async def check_duplicates(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    exclude_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up existing candidates by email/phone before creating a new one."""
    dups = await find_duplicates(db, email, phone, exclude_id)
    return {"duplicates": [{"id": d.id, "name": d.name, "email": d.email, "phone": d.phone} for d in dups]}


@router.post("/", status_code=201)
async def create_candidate(
    payload: CandidateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dups = await find_duplicates(db, payload.email, payload.phone)
    if dups:
        raise _duplicate_error(dups)
    data = payload.model_dump(exclude_none=True)
    data["email"] = normalize_email(payload.email)
    candidate = Candidate(**data, phone_normalized=normalize_phone(payload.phone), created_by_id=current_user.id)
    db.add(candidate)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Added candidate {candidate.name}", "candidate",
                 candidate.id, request=request)
    await db.commit()
    await db.refresh(candidate)
    return _serialize(candidate)


@router.get("/{candidate_id}")
async def get_candidate(candidate_id: int, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    c = await _get(db, candidate_id)
    data = _serialize(c)
    notes = (await db.execute(
        select(CandidateNote).where(CandidateNote.candidate_id == candidate_id).order_by(CandidateNote.created_at.desc())
    )).scalars().all()
    data["candidate_notes"] = [
        {"id": n.id, "content": n.content, "type": n.type, "created_at": n.created_at.isoformat()} for n in notes
    ]
    return data


@router.put("/{candidate_id}")
async def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = await _get(db, candidate_id)
    data = payload.model_dump(exclude_none=True)
    if "email" in data or "phone" in data:
        dups = await find_duplicates(db, data.get("email"), data.get("phone"), exclude_id=c.id)
        if dups:
            raise _duplicate_error(dups)
        if "email" in data:
            data["email"] = normalize_email(data["email"])
        if "phone" in data:
            c.phone_normalized = normalize_phone(data["phone"])
    old_status = c.status
    changes = diff(c, data)
    for field, val in data.items():
        setattr(c, field, val)
    c.updated_at = datetime.now(timezone.utc)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated candidate {c.name}", "candidate", c.id,
                     changes=changes, request=request)
    status_changed = "status" in data and data["status"] != old_status
    if status_changed:
        notify(db, [c.created_by_id], f"Candidate moved to {c.status.value}", c.name, NotifType.candidate_update,
               f"/candidates/{c.id}", exclude=current_user.id)
    await db.commit()
    if status_changed and c.email and c.status in _EMAIL_ON_STATUS:
        from app.services.email import send_candidate_status_email
        await queue_email(send_candidate_status_email, c.email, c.name, c.status.value, None)
    return _serialize(c)


@router.delete("/{candidate_id}")
async def delete_candidate(candidate_id: int, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_owner)):
    c = await _get(db, candidate_id)
    if (await db.execute(select(func.count()).select_from(Placement).where(Placement.candidate_id == c.id))).scalar():
        raise HTTPException(409, "This candidate has placements linked to billing and can't be deleted")
    await db.execute(update(Interview).where(Interview.candidate_id == c.id).values(application_id=None))
    for iv in (await db.execute(select(Interview).where(Interview.candidate_id == c.id))).scalars().all():
        await db.delete(iv)
    log_activity(db, current_user, ActivityType.delete, f"Deleted candidate {c.name}", "candidate", c.id,
                 request=request)
    await db.delete(c)
    await db.commit()
    return {"message": "Candidate deleted"}


@router.post("/{keep_id}/merge/{duplicate_id}")
async def merge_candidates(keep_id: int, duplicate_id: int, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_owner)):
    """Merge a duplicate into the record being kept: applications, notes, interviews
    and placements move over; empty fields are filled from the duplicate."""
    if keep_id == duplicate_id:
        raise HTTPException(400, "Choose two different candidates")
    keep, dup = await _get(db, keep_id), await _get(db, duplicate_id)

    keep_jobs = set((await db.execute(select(Application.job_id).where(Application.candidate_id == keep.id))).scalars())
    for app in (await db.execute(select(Application).where(Application.candidate_id == dup.id))).scalars().all():
        if app.job_id in keep_jobs:
            await db.execute(update(Interview).where(Interview.application_id == app.id).values(application_id=None))
            await db.delete(app)          # same job on both records: keep the surviving one
        else:
            app.candidate_id = keep.id
    keep_placed_jobs = set((await db.execute(select(Placement.job_id).where(Placement.candidate_id == keep.id))).scalars())
    for pl in (await db.execute(select(Placement).where(Placement.candidate_id == dup.id))).scalars().all():
        if pl.job_id in keep_placed_jobs:
            raise HTTPException(409, "Both records have a placement for the same job; resolve that first")
        pl.candidate_id = keep.id
    await db.execute(update(CandidateNote).where(CandidateNote.candidate_id == dup.id).values(candidate_id=keep.id))
    await db.execute(update(Interview).where(Interview.candidate_id == dup.id).values(candidate_id=keep.id))

    filled = {}
    for field in ("email", "phone", "current_title", "current_company", "location", "expected_salary",
                  "notice_period", "linkedin_url", "resume_url", "experience_years"):
        if not getattr(keep, field) and getattr(dup, field):
            setattr(keep, field, getattr(dup, field))
            filled[field] = getattr(dup, field)
    keep.skills = sorted(set((keep.skills or []) + (dup.skills or [])), key=str.lower)
    keep.phone_normalized = normalize_phone(keep.phone)
    keep.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.merge, f"Merged candidate #{dup.id} ({dup.name}) into #{keep.id}",
                 "candidate", keep.id, changes={"merged_from": dup.id, "filled": filled}, request=request)
    await db.flush()
    await db.delete(dup)
    await db.commit()
    await db.refresh(keep)
    return _serialize(keep)


@router.post("/{candidate_id}/resume")
async def upload_resume(
    candidate_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload_user_limiter.check(f"u{current_user.id}", "Too many uploads. Please wait a few minutes.")
    c = await _get(db, candidate_id)
    c.resume_url = await save_document(file, "resumes", f"c{candidate_id}")
    c.updated_at = datetime.now(timezone.utc)
    log_activity(db, current_user, ActivityType.file_upload, f"Uploaded resume for {c.name}", "candidate", c.id,
                 request=request)
    await db.commit()
    return {"resume_url": sign_url(c.resume_url)}


@router.post("/{candidate_id}/ats-score")
async def compute_ats_score(
    candidate_id: int,
    job_skills: List[str],
    required_experience: float = Query(0, ge=0, le=60),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = await _get(db, candidate_id)
    score = _compute_ats_score(c, job_skills[:100], required_experience)
    c.ats_score = score
    c.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ats_score": score, "candidate_id": candidate_id}


@router.post("/{candidate_id}/notes", status_code=201)
async def add_note(
    candidate_id: int,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get(db, candidate_id)
    note = CandidateNote(candidate_id=candidate_id, content=payload.content, type=payload.type,
                         created_by_id=current_user.id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return {"id": note.id, "content": note.content, "type": note.type, "created_at": note.created_at.isoformat()}


@router.get("/{candidate_id}/notes")
async def get_notes(candidate_id: int, db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    await _get(db, candidate_id)
    notes = (await db.execute(
        select(CandidateNote).where(CandidateNote.candidate_id == candidate_id).order_by(CandidateNote.created_at.desc())
    )).scalars().all()
    return [{"id": n.id, "content": n.content, "type": n.type, "created_at": n.created_at.isoformat()} for n in notes]


@router.get("/{candidate_id}/history")
async def candidate_history(candidate_id: int, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    """ATS stage history across all of the candidate's applications."""
    await _get(db, candidate_id)
    rows = (await db.execute(
        select(ApplicationEvent, Application.job_id)
        .join(Application, Application.id == ApplicationEvent.application_id)
        .where(Application.candidate_id == candidate_id)
        .order_by(ApplicationEvent.id)
    )).all()
    return [{"application_id": e.application_id, "job_id": job_id, "from_stage": e.from_stage,
             "to_stage": e.to_stage, "actor_id": e.actor_id, "note": e.note,
             "created_at": e.created_at.isoformat()} for e, job_id in rows]
