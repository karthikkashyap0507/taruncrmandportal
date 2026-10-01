"""
CRM Database Models - JobsNexGen CRM
PostgreSQL schema aligned with API routes and frontend.
"""
import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, Enum,
    ForeignKey, JSON, UniqueConstraint, Table, Column, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    owner = "owner"
    bdm = "bdm"
    hr = "hr"


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    proposal = "proposal"
    negotiation = "negotiation"
    converted = "converted"
    lost = "lost"


class LeadTemperature(str, enum.Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"


class CandidateStatus(str, enum.Enum):
    new = "new"
    screening = "screening"
    shortlisted = "shortlisted"
    interviewing = "interviewing"
    offered = "offered"
    placed = "placed"
    rejected = "rejected"


class InterviewType(str, enum.Enum):
    video = "video"
    phone = "phone"
    in_person = "in_person"
    technical = "technical"
    hr = "hr"


class InterviewStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class JobStatus(str, enum.Enum):
    open = "open"
    on_hold = "on_hold"
    closed = "closed"
    filled = "filled"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class NotifType(str, enum.Enum):
    lead_assigned = "lead_assigned"
    interview_scheduled = "interview_scheduled"
    follow_up = "follow_up"
    status_changed = "status_changed"
    task_assigned = "task_assigned"
    candidate_update = "candidate_update"
    application_stage = "application_stage"
    interview_updated = "interview_updated"
    interview_reminder = "interview_reminder"
    joining = "joining"
    placement = "placement"
    invoice = "invoice"
    incentive = "incentive"
    system = "system"


class ActivityType(str, enum.Enum):
    login = "login"
    logout = "logout"
    create = "create"
    update = "update"
    delete = "delete"
    email_sent = "email_sent"
    call_logged = "call_logged"
    note_added = "note_added"
    status_change = "status_change"
    file_upload = "file_upload"
    assign = "assign"
    approve = "approve"
    payment = "payment"
    merge = "merge"
    security = "security"
    export = "export"


# ── Association tables ──────────────────────────────────────────────────────────

interview_interviewers = Table(
    "crm_interview_interviewers",
    Base.metadata,
    Column("interview_id", Integer, ForeignKey("crm_interviews.id", ondelete="CASCADE")),
    Column("user_id", Integer, ForeignKey("crm_users.id", ondelete="CASCADE")),
)


# ── Core Models ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "crm_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.hr)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    activities: Mapped[List["ActivityLog"]] = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    assigned_leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="assigned_to", foreign_keys="Lead.assigned_to_id")
    created_leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="created_by", foreign_keys="Lead.created_by_id")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="assigned_to", foreign_keys="Task.assigned_to_id")


class UserSession(Base):
    __tablename__ = "crm_user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id", ondelete="CASCADE"), index=True)
    refresh_token: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class PasswordResetToken(Base):
    __tablename__ = "crm_password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Company / Client Models ────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "crm_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_leads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    contacts: Mapped[List["Contact"]] = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    jobs: Mapped[List["CRMJob"]] = relationship("CRMJob", back_populates="company")


class Contact(Base):
    __tablename__ = "crm_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped["Company"] = relationship("Company", back_populates="contacts")


# ── Lead / Pipeline Models ─────────────────────────────────────────────────────

class Lead(Base):
    __tablename__ = "crm_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    contact_name: Mapped[str] = mapped_column(String(120))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.new, index=True)
    temperature: Mapped[LeadTemperature] = mapped_column(Enum(LeadTemperature), default=LeadTemperature.cold)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requirement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_positions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True, index=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_to: Mapped[Optional["User"]] = relationship("User", back_populates="assigned_leads", foreign_keys=[assigned_to_id])
    created_by: Mapped[Optional["User"]] = relationship("User", back_populates="created_leads", foreign_keys=[created_by_id])
    lead_notes: Mapped[List["LeadNote"]] = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    followups: Mapped[List["FollowUp"]] = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")


class LeadNote(Base):
    __tablename__ = "crm_lead_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_leads.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="lead_notes")
    created_by: Mapped["User"] = relationship("User")


class FollowUp(Base):
    __tablename__ = "crm_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_leads.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50), default="call")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="followups")
    created_by: Mapped["User"] = relationship("User")


# ── Candidate Models ───────────────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "crm_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Digits only (last 10), used to detect duplicate candidates regardless of formatting
    phone_normalized: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    current_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    experience_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_salary: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notice_period: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    resume_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ats_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[CandidateStatus] = mapped_column(Enum(CandidateStatus), default=CandidateStatus.new, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    portal_candidate_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    candidate_notes: Mapped[List["CandidateNote"]] = relationship("CandidateNote", back_populates="candidate", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


class CandidateNote(Base):
    __tablename__ = "crm_candidate_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_candidates.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(50), default="general")
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="candidate_notes")
    created_by: Mapped["User"] = relationship("User")


# ── Job Models ─────────────────────────────────────────────────────────────────

class CRMJob(Base):
    __tablename__ = "crm_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_companies.id"), nullable=True, index=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="full-time")
    experience_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skills_required: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    positions: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.open, index=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="crm")
    portal_job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="jobs")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "crm_applications"
    __table_args__ = (Index("uq_crm_applications_job_candidate", "job_id", "candidate_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_candidates.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(50), default="applied", index=True)
    stage_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["CRMJob"] = relationship("CRMJob", back_populates="applications")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="applications")
    interviews: Mapped[List["Interview"]] = relationship("Interview", back_populates="application", cascade="all, delete-orphan")


# ── Interview Models ───────────────────────────────────────────────────────────

class Interview(Base):
    __tablename__ = "crm_interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_applications.id", ondelete="SET NULL"), nullable=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_jobs.id"), index=True)
    type: Mapped[InterviewType] = mapped_column(Enum(InterviewType), default=InterviewType.video)
    status: Mapped[InterviewStatus] = mapped_column(Enum(InterviewStatus), default=InterviewStatus.scheduled)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    location_or_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scheduled_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="interviews")
    candidate: Mapped["Candidate"] = relationship("Candidate")
    job: Mapped["CRMJob"] = relationship("CRMJob")
    scheduled_by: Mapped[Optional["User"]] = relationship("User")
    interviewers: Mapped[List["User"]] = relationship("User", secondary=interview_interviewers, viewonly=False)


# ── Task Models ────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "crm_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.medium)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.todo, index=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True, index=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_to: Mapped[Optional["User"]] = relationship("User", back_populates="tasks", foreign_keys=[assigned_to_id])
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])


# ── Notification / Activity Models ─────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "crm_notifications"
    __table_args__ = (Index("ix_crm_notifications_user_read", "user_id", "read"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[NotifType] = mapped_column(Enum(NotifType), default=NotifType.system)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


class ActivityLog(Base):
    __tablename__ = "crm_activity_logs"
    __table_args__ = (Index("ix_crm_activity_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id", ondelete="CASCADE"), index=True)
    action: Mapped[ActivityType] = mapped_column(Enum(ActivityType))
    # Field-level before/after values for updates (who changed what)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User"] = relationship("User", back_populates="activities")

# ── ATS stage history ─────────────────────────────────────────────────────────

class ApplicationEvent(Base):
    __tablename__ = "crm_application_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_applications.id", ondelete="CASCADE"), index=True)
    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50))
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Email outbox (every email; failures are kept and retried) ────────────────

class EmailOutbox(Base):
    __tablename__ = "crm_email_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    to_email: Mapped[str] = mapped_column(String(255))
    to_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(255))
    html: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|sent|failed|dead
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Agreements (MOU) -> Placements (joining) -> Invoices (billing) -> Incentives

class AgreementStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    expired = "expired"
    terminated = "terminated"


class FeeType(str, enum.Enum):
    percentage = "percentage"   # % of the candidate's annual CTC
    fixed = "fixed"             # fixed amount per placement


class Agreement(Base):
    """MOU with a client: the fee terms every placement and invoice is billed on."""
    __tablename__ = "crm_agreements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    fee_type: Mapped[FeeType] = mapped_column(Enum(FeeType), default=FeeType.percentage)
    fee_value: Mapped[float] = mapped_column(Float)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    replacement_guarantee_days: Mapped[int] = mapped_column(Integer, default=90)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AgreementStatus] = mapped_column(Enum(AgreementStatus), default=AgreementStatus.draft, index=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    company: Mapped["Company"] = relationship("Company")


class PlacementStatus(str, enum.Enum):
    offered = "offered"
    joined = "joined"
    dropped = "dropped"                      # offer accepted but never joined
    left_in_guarantee = "left_in_guarantee"  # joined, then left within the replacement period


class Placement(Base):
    """A candidate placed with a client under an MOU. Fee terms are copied from the
    MOU when the offer is recorded, so later MOU edits never change past billing."""
    __tablename__ = "crm_placements"
    __table_args__ = (Index("uq_crm_placements_candidate_job", "candidate_id", "job_id", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_jobs.id"), index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_companies.id"), index=True)
    agreement_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_agreements.id"), index=True)
    recruiter_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True, index=True)
    bdm_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True, index=True)
    offered_ctc: Mapped[float] = mapped_column(Float)
    offer_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected_joining_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    left_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PlacementStatus] = mapped_column(Enum(PlacementStatus), default=PlacementStatus.offered, index=True)
    fee_type: Mapped[FeeType] = mapped_column(Enum(FeeType))
    fee_value: Mapped[float] = mapped_column(Float)
    fee_amount: Mapped[float] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    joining_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate: Mapped["Candidate"] = relationship("Candidate")
    job: Mapped["CRMJob"] = relationship("CRMJob")
    company: Mapped["Company"] = relationship("Company")
    agreement: Mapped["Agreement"] = relationship("Agreement")


class InvoiceStatus(str, enum.Enum):
    sent = "sent"
    paid = "paid"
    cancelled = "cancelled"


class Invoice(Base):
    """At most one non-cancelled invoice per placement; amounts come from the MOU terms."""
    __tablename__ = "crm_invoices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    placement_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_placements.id"), index=True)
    agreement_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_agreements.id"), index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_companies.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    gst_rate: Mapped[float] = mapped_column(Float, default=18.0)
    gst_amount: Mapped[float] = mapped_column(Float)
    total_amount: Mapped[float] = mapped_column(Float)
    amount_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.sent, index=True)
    paid_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    overdue_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    placement: Mapped["Placement"] = relationship("Placement")
    company: Mapped["Company"] = relationship("Company")


class IncentiveRule(Base):
    """Incentive (royalty/commission) rate per role, as a % of the invoice amount
    before GST. Only the owner can change these."""
    __tablename__ = "crm_incentive_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), unique=True)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    updated_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class IncentiveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    paid = "paid"
    void = "void"


class Incentive(Base):
    """Server-computed payout for a team member on a paid invoice."""
    __tablename__ = "crm_incentives"
    __table_args__ = (Index("uq_crm_incentives_invoice_user", "invoice_id", "user_id", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_users.id"), index=True)
    placement_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_placements.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_invoices.id"), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    basis_amount: Mapped[float] = mapped_column(Float)
    rate: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[IncentiveStatus] = mapped_column(Enum(IncentiveStatus), default=IncentiveStatus.pending, index=True)
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crm_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
