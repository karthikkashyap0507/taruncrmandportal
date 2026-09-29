from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    headline: Mapped[str | None] = mapped_column(String(500))
    skills: Mapped[list | None] = mapped_column(JSON, default=list)
    experience: Mapped[list | None] = mapped_column(JSON, default=list)
    resume_url: Mapped[str | None] = mapped_column(String(500))
    profile_score: Mapped[float | None] = mapped_column(Float, default=0.0)

    user = relationship("User", back_populates="candidate")
    applications = relationship("Application", back_populates="candidate")
