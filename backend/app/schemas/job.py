from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.application import ApplicationStatus
from app.models.job import JobStatus
from app.models.message import MessageType


class CompanyResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    model_config = {"from_attributes": True}


class CandidateInfo(BaseModel):
    """Candidate profile info shown to recruiters on an application."""
    user_id: int
    name: str
    email: str
    headline: Optional[str] = None
    skills: list = []
    resume_url: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    status: ApplicationStatus
    score: Optional[float] = None
    applied_at: datetime
    full_name: Optional[str] = None
    phone: Optional[str] = None
    years_experience: Optional[int] = None
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None
    candidate_info: Optional[CandidateInfo] = None
    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    years_experience: Optional[int] = Field(default=None, ge=0, le=60)
    cover_letter: Optional[str] = Field(default=None, max_length=10000)
    resume_url: Optional[str] = Field(default=None, max_length=500)


class ApplicationUpdate(BaseModel):
    # The ATS score is always computed by the server; recruiters cannot set it.
    status: Optional[ApplicationStatus] = None
    note: Optional[str] = Field(default=None, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    application_id: int
    sender_id: int
    sender_name: str
    message_type: MessageType
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageType = MessageType.message


def _clean_skills(v):
    if v is None:
        return v
    out, seen = [], set()
    for s in v:
        s = str(s).strip()[:60]
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out[:50]


def _check_salary(salary_min, salary_max):
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise ValueError("Minimum salary cannot be greater than maximum salary")


class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=20000)
    company_id: Optional[int] = None
    salary_min: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    salary_max: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    skills: list[str] = []
    experience_level: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=255)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    status: JobStatus = JobStatus.published

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        return _clean_skills(v)

    @model_validator(mode="after")
    def salary_range(self):
        _check_salary(self.salary_min, self.salary_max)
        return self


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=10, max_length=20000)
    salary_min: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    salary_max: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    skills: Optional[list[str]] = None
    experience_level: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=255)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    status: Optional[JobStatus] = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        return _clean_skills(v)

    @model_validator(mode="after")
    def salary_range(self):
        _check_salary(self.salary_min, self.salary_max)
        return self


class JobResponse(BaseModel):
    id: int
    company_id: int
    recruiter_id: int
    title: str
    description: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    skills: Optional[list]
    experience_level: Optional[str]
    location: Optional[str]
    employment_type: Optional[str]
    status: JobStatus
    company: Optional[CompanyResponse] = None
    model_config = {"from_attributes": True}
