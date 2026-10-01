from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CandidateUpdate(BaseModel):
    headline: Optional[str] = Field(default=None, max_length=500)
    skills: Optional[List[str]] = Field(default=None, max_length=100)
    experience: Optional[List[dict]] = Field(default=None, max_length=50)
    resume_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        if v is None:
            return v
        out, seen = [], set()
        for s in v:
            s = str(s).strip()[:100]
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        return out


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
