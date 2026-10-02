from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    logo: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(100))
    # Set for client companies the CRM publishes jobs for, so employer accounts can't manage them
    external_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    jobs = relationship("Job", back_populates="company")
    recruiters = relationship("Recruiter", back_populates="company")
