import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OutreachQueueItem(Base):
    __tablename__ = "outreach_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )

    # Outreach details
    use_case: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'mujertech', 'cascadia', 'job_search'
    outreach_type: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'resurrection', 'warm', 'cold'
    purpose: Mapped[str] = mapped_column(
        Text, nullable=False, default="reconnect"
    )  # 'reconnect', 'introduce', 'follow_up', etc.
    generated_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status workflow: draft → approved → sent → responded
    status: Mapped[str] = mapped_column(
        Text, default="draft"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    contact: Mapped["Contact"] = relationship(
        "Contact", back_populates="outreach_queue_items"
    )

    def __repr__(self) -> str:
        return f"<OutreachQueueItem {self.use_case}/{self.purpose} - {self.status}>"
