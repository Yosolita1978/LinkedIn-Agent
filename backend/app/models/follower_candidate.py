import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FollowerCandidate(Base):
    """
    A persistent backlog of people you follow who aren't connections yet.

    Scans upsert into this table (deduped by identity_key) so you can work
    through a large Following list across many sessions instead of re-scanning.
    A candidate leaves the backlog when it becomes "requested" or "skipped".
    """

    __tablename__ = "follower_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # The /in/<id> public identifier, lowercased — the ONLY dedup key (never the
    # display name, which collides). Unique so re-scans skip people already here.
    identity_key: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )

    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    segments: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    # The generated/edited connection note (filled when status reaches "noted").
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle: new → noted → requested | skipped
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", index=True
    )

    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<FollowerCandidate {self.name} ({self.status})>"
