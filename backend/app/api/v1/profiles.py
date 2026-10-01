from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.core.files import own_resume_ref, sign_resume_url
from app.models.candidate import Candidate
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.schemas.profile import CandidateResponse, CandidateUpdate, RecruiterResponse

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _candidate_out(candidate: Candidate) -> CandidateResponse:
    out = CandidateResponse.model_validate(candidate)
    out.skills = candidate.skills or []
    out.experience = candidate.experience or []
    # The owner gets a fresh signed link to their own resume
    out.resume_url = sign_resume_url(candidate.resume_url)
    return out


def _my_candidate(db: Session, user: User) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return candidate


@router.get("/me", response_model=CandidateResponse | RecruiterResponse)
def get_my_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.candidate:
        return _candidate_out(_my_candidate(db, user))
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    return RecruiterResponse.model_validate(recruiter)


@router.get("/candidate/me", response_model=CandidateResponse)
def get_candidate_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _candidate_out(_my_candidate(db, user))


@router.patch("/candidate/me", response_model=CandidateResponse)
def update_candidate_profile(
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = _my_candidate(db, user)
    data = payload.model_dump(exclude_unset=True)
    if "resume_url" in data:
        data["resume_url"] = own_resume_ref(data["resume_url"], user.id)
    for key, value in data.items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return _candidate_out(candidate)


@router.get("/recruiter/me", response_model=RecruiterResponse)
def get_recruiter_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    return RecruiterResponse.model_validate(recruiter)
