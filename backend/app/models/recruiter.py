from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recruiter(Base):
    __tablename__ = "recruiters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))

    user = relationship("User", back_populates="recruiter")
    company = relationship("Company", back_populates="recruiters")
    jobs = relationship("Job", back_populates="recruiter")
