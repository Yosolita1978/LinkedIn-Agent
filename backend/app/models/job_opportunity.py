import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobOpportunity(Base):
    """
    A job posting found by a LinkedIn Jobs search.

    Searches upsert into this table (deduped by linkedin_job_id), so running the
    same search again only adds new postings and keeps your status and notes.
    """

    __tablename__ = "job_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # The numeric id from /jobs/view/<id>. The only dedup key.
    linkedin_job_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    company: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Full text of the search-result card (salary, "Easy Apply", posted date...).
    # Kept raw because LinkedIn's card layout changes often.
    card_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Full posting text from the job page (truncated to 15,000 chars).
    # Only fetched on request, for jobs worth a closer look.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # The search keywords that first found this job.
    search_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle: new → interested → applied | skipped
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<JobOpportunity {self.title} @ {self.company} ({self.status})>"
