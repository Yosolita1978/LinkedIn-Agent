import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )

    # Message data
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # 'sent' or 'received'
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Analysis
    is_substantive: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )  # calculated: length > threshold, not just "thanks"

    # LinkedIn metadata
    conversation_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Record timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.direction} {self.date}>"
