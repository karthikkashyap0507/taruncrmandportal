import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offered = "offered"
    rejected = "rejected"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.applied
    )
    score: Mapped[float | None] = mapped_column(Float)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Candidate application details
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    years_experience: Mapped[int | None] = mapped_column(Integer)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    resume_url: Mapped[str | None] = mapped_column(String(500))

    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    messages = relationship("ApplicationMessage", back_populates="application", cascade="all, delete-orphan")
