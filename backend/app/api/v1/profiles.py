from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.schemas.profile import CandidateResponse, CandidateUpdate, RecruiterResponse

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=CandidateResponse | RecruiterResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.candidate:
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        return CandidateResponse.model_validate(candidate)
    else:
        recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
        if not recruiter:
            raise HTTPException(status_code=404, detail="Recruiter profile not found")
        return RecruiterResponse.model_validate(recruiter)


@router.get("/candidate/me", response_model=CandidateResponse)
def get_candidate_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return CandidateResponse.model_validate(candidate)


@router.patch("/candidate/me", response_model=CandidateResponse)
def update_candidate_profile(
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return CandidateResponse.model_validate(candidate)


@router.get("/recruiter/me", response_model=RecruiterResponse)
def get_recruiter_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    recruiter = db.query(Recruiter).filter(Recruiter.user_id == user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    return RecruiterResponse.model_validate(recruiter)
