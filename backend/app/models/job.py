import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"      # waiting for a platform admin to approve it
    published = "published"
    rejected = "rejected"    # an admin turned it down (reason in review_note)
    closed = "closed"


# Minimum qualification a job asks for (the website shows friendly labels)
EDUCATION_LEVELS = ("any", "10th", "12th", "iti", "diploma", "graduate", "postgraduate")
SALARY_PERIODS = ("month", "year")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    recruiter_id: Mapped[int] = mapped_column(ForeignKey("recruiters.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    skills: Mapped[list | None] = mapped_column(JSON, default=list)
    experience_level: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))       # city, e.g. Bengaluru
    locality: Mapped[str | None] = mapped_column(String(120))       # area, e.g. JP Nagar
    education: Mapped[str | None] = mapped_column(String(20), index=True)
    salary_period: Mapped[str | None] = mapped_column(String(10))   # month | year (older jobs: year)
    employment_type: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.published, index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Bumped on every change; the CRM pulls jobs changed since its last sync
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True,
                                                        default=_utcnow, onupdate=_utcnow)

    company = relationship("Company", back_populates="jobs")
    recruiter = relationship("Recruiter", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
