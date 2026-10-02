from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.application import ApplicationStatus
from app.models.job import EDUCATION_LEVELS, SALARY_PERIODS, JobStatus
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
    education: Optional[str] = None
    expected_salary: Optional[int] = None
    current_location: Optional[str] = None
    job_title: Optional[str] = None
    candidate_info: Optional[CandidateInfo] = None
    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    years_experience: Optional[int] = Field(default=None, ge=0, le=60)
    cover_letter: Optional[str] = Field(default=None, max_length=10000)
    resume_url: Optional[str] = Field(default=None, max_length=500)
    education: Optional[str] = None
    expected_salary: Optional[int] = Field(default=None, ge=0, le=100_000_000)  # ₹ per month
    current_location: Optional[str] = Field(default=None, max_length=255)

    @field_validator("education")
    @classmethod
    def known_education(cls, v):
        return _check_education(v)


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


def _check_education(v):
    if v in (None, ""):
        return None
    if v not in EDUCATION_LEVELS:
        raise ValueError(f"education must be one of: {', '.join(EDUCATION_LEVELS)}")
    return v


def _check_period(v):
    if v in (None, ""):
        return None
    if v not in SALARY_PERIODS:
        raise ValueError("salary_period must be 'month' or 'year'")
    return v


def _strip(v):
    return " ".join(v.split()) if isinstance(v, str) else v


class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=20000)
    company_id: Optional[int] = None
    salary_min: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    salary_max: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    skills: list[str] = []
    experience_level: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=255)
    locality: Optional[str] = Field(default=None, max_length=120)
    education: Optional[str] = None
    salary_period: Optional[str] = "month"
    employment_type: Optional[str] = Field(default=None, max_length=50)
    status: JobStatus = JobStatus.published  # employers' "published" becomes "pending" until approved

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        return _clean_skills(v)

    @field_validator("location", "locality", mode="before")
    @classmethod
    def tidy(cls, v):
        return _strip(v) or None

    @field_validator("education")
    @classmethod
    def known_education(cls, v):
        return _check_education(v)

    @field_validator("salary_period")
    @classmethod
    def known_period(cls, v):
        return _check_period(v)

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
    locality: Optional[str] = Field(default=None, max_length=120)
    education: Optional[str] = None
    salary_period: Optional[str] = None
    employment_type: Optional[str] = Field(default=None, max_length=50)
    status: Optional[JobStatus] = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        return _clean_skills(v)

    @field_validator("location", "locality", mode="before")
    @classmethod
    def tidy(cls, v):
        return _strip(v) or None

    @field_validator("education")
    @classmethod
    def known_education(cls, v):
        return _check_education(v)

    @field_validator("salary_period")
    @classmethod
    def known_period(cls, v):
        return _check_period(v)

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
    locality: Optional[str] = None
    education: Optional[str] = None
    salary_period: Optional[str] = None
    employment_type: Optional[str]
    status: JobStatus
    review_note: Optional[str] = None
    is_premium: bool = False
    source: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    company: Optional[CompanyResponse] = None
    model_config = {"from_attributes": True}
