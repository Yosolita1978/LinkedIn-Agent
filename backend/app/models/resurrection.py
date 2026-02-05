import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResurrectionOpportunity(Base):
    __tablename__ = "resurrection_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )

    # Hook details
    hook_type: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'dormant', 'promise_made', 'question_unanswered', 'they_waiting'
    hook_detail: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # context/excerpt that triggered detection

    # Source reference
    source_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # set false after user addresses it

    # Relationships
    contact: Mapped["Contact"] = relationship(
        "Contact", back_populates="resurrection_opportunities"
    )
    source_message: Mapped[Optional["Message"]] = relationship("Message")

    # One active hook per type per contact
    __table_args__ = (
        UniqueConstraint("contact_id", "hook_type", name="uq_contact_hook_type"),
    )

    def __repr__(self) -> str:
        return f"<ResurrectionOpportunity {self.hook_type} for contact {self.contact_id}>"
