from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
import os, shutil, uuid

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models import Candidate, CandidateNote, CandidateStatus, User, Application

router = APIRouter(prefix="/candidates", tags=["candidates"])


class CandidateCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    expected_salary: Optional[str] = None
    notice_period: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: CandidateStatus = CandidateStatus.new
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    portal_candidate_id: Optional[int] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    expected_salary: Optional[str] = None
    notice_period: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: Optional[CandidateStatus] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    ats_score: Optional[int] = None


class NoteCreate(BaseModel):
    content: str
    type: Optional[str] = "general"


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
        "resume_url": c.resume_url,
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


@router.get("/")
async def list_candidates(
    status: Optional[str] = None,
    search: Optional[str] = Query(None),
    skill: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Candidate)
    if status:
        query = query.where(Candidate.status == status)
    if search:
        query = query.where(
            or_(
                Candidate.name.ilike(f"%{search}%"),
                Candidate.email.ilike(f"%{search}%"),
                Candidate.current_title.ilike(f"%{search}%"),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    query = query.order_by(Candidate.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    candidates = result.scalars().all()
    return {"total": total, "page": page, "limit": limit, "data": [_serialize(c) for c in candidates]}


@router.post("/", status_code=201)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = Candidate(**payload.model_dump(exclude_none=True), created_by_id=current_user.id)
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return _serialize(candidate)


@router.get("/{candidate_id}")
async def get_candidate(candidate_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Candidate not found")
    data = _serialize(c)

    notes_result = await db.execute(
        select(CandidateNote).where(CandidateNote.candidate_id == candidate_id).order_by(CandidateNote.created_at.desc())
    )
    data["candidate_notes"] = [
        {"id": n.id, "content": n.content, "type": n.type, "created_at": n.created_at.isoformat()}
        for n in notes_result.scalars().all()
    ]
    return data


@router.put("/{candidate_id}")
async def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Candidate not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(c, field, val)
    c.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _serialize(c)


@router.delete("/{candidate_id}")
async def delete_candidate(candidate_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Candidate not found")
    await db.delete(c)
    await db.commit()
    return {"message": "Candidate deleted"}


@router.post("/{candidate_id}/resume")
async def upload_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Candidate not found")

    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in [".pdf", ".doc", ".docx"]:
        raise HTTPException(400, "Only PDF, DOC, DOCX allowed")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "resumes")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    c.resume_url = f"/uploads/resumes/{filename}"
    await db.commit()
    return {"resume_url": c.resume_url}


@router.post("/{candidate_id}/ats-score")
async def compute_ats_score(
    candidate_id: int,
    job_skills: List[str],
    required_experience: float = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Candidate not found")
    score = _compute_ats_score(c, job_skills, required_experience)
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
    note = CandidateNote(candidate_id=candidate_id, content=payload.content, type=payload.type, created_by_id=current_user.id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return {"id": note.id, "content": note.content, "type": note.type, "created_at": note.created_at.isoformat()}


@router.get("/{candidate_id}/notes")
async def get_notes(candidate_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(CandidateNote).where(CandidateNote.candidate_id == candidate_id).order_by(CandidateNote.created_at.desc())
    )
    return [
        {"id": n.id, "content": n.content, "type": n.type, "created_at": n.created_at.isoformat()}
        for n in result.scalars().all()
    ]
