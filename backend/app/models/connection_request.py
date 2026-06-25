import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConnectionRequest(Base):
    __tablename__ = "connection_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    segments: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    note_sent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status progression:
    #   pending → accepted → conversation_queued   (happy path)
    # Other terminal/outcome states (set at send time or on detection):
    #   already_connected, already_pending, failed, rejected, withdrawn
    # 'conversation_queued' means acceptance was detected AND a first-touch
    # message has been generated and inserted into the outreach queue as a draft.
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )

    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    def __repr__(self) -> str:
        return f"<ConnectionRequest {self.name} ({self.status})>"
