from datetime import datetime
from typing import Optional
from pydantic import BaseModel

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
    full_name: Optional[str] = None
    phone: Optional[str] = None
    years_experience: Optional[int] = None
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    score: Optional[float] = None


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
    content: str
    message_type: MessageType = MessageType.message


class JobCreate(BaseModel):
    title: str
    description: str
    company_id: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    skills: list[str] = []
    experience_level: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    status: JobStatus = JobStatus.published


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    skills: Optional[list[str]] = None
    experience_level: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    status: Optional[JobStatus] = None


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
