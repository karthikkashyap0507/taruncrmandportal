from pydantic import BaseModel
from typing import List, Optional


class CandidateUpdate(BaseModel):
    headline: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[dict]] = None
    resume_url: Optional[str] = None


class CandidateResponse(BaseModel):
    id: int
    user_id: int
    headline: Optional[str] = None
    skills: List[str] = []
    experience: List[dict] = []
    resume_url: Optional[str] = None
    profile_score: float = 0.0

    model_config = {"from_attributes": True}


class RecruiterUpdate(BaseModel):
    pass


class RecruiterResponse(BaseModel):
    id: int
    user_id: int
    company_id: int

    model_config = {"from_attributes": True}
