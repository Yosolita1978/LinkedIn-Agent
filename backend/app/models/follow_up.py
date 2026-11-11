import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FollowUp(Base):
    """
    One person + one opportunity you're working, with what happened last and
    what to do next. Example: "Anand Joshi @ McGraw Hill — send availability, due Nov 12".

    Every logged touch is appended to `history`, so the whole thread is visible.
    """

    __tablename__ = "follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    profile_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

    # Optional links to where this thread came from.
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_opportunities.id", ondelete="SET NULL"), nullable=True
    )
    post_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hiring_posts.id", ondelete="SET NULL"), nullable=True
    )

    # requested → connected → talking → call_scheduled → interviewing → closed (or no_response)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="requested", index=True)
    # open while there's something to do; done once closed
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open", index=True)

    last_touch_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_touch: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    # [{"at": "2026-11-10T19:40:00", "summary": "...", "stage": "talking"}, ...]
    history: Mapped[list[dict[str, Optional[str]]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<FollowUp {self.name} @ {self.company} ({self.stage}, due {self.due_date})>"
