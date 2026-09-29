import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MessageType(str, enum.Enum):
    message = "message"
    approval = "approval"
    rejection = "rejection"
    interview_invite = "interview_invite"
    offer = "offer"


class ApplicationMessage(Base):
    __tablename__ = "application_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.message)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="messages")
    sender = relationship("User")
