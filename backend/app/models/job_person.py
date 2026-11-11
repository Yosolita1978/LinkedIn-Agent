import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobPerson(Base):
    """
    A person linked to a saved job: someone LinkedIn suggests reaching out to,
    the hiring team, or a 1st/2nd-degree connection who works at the company.

    Rows for a (job, source) pair are replaced each time that source is scraped,
    so the list always reflects the latest scan.
    """

    __tablename__ = "job_people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Where we found them:
    #   reach_out     → job page "People you can reach out to"
    #   hiring_team   → job page "Meet the hiring team" (older layout)
    #   company_page  → the company's People page (1st/2nd degree only)
    #   network_hint  → a summary with no names, e.g. "Danny and others in your network"
    source: Mapped[str] = mapped_column(String(20), nullable=False)

    name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    degree: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 1st, 2nd, 3rd+
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Why LinkedIn shows them, e.g. "School alum from University of Washington"
    # or "David and 5 other mutual connections".
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Set when this person is already in your contacts.
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<JobPerson {self.name} ({self.source}, {self.degree})>"
