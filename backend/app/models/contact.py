import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Text, Integer, Date, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    linkedin_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Structured data from scraping
    experience: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    education: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    connection_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Warmth scoring (0-100 scale)
    warmth_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warmth_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # {recency: 25, frequency: 15, depth: 30, responsiveness: 20, initiation: 10}
    warmth_calculated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Segmentation
    segment_tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )  # auto-detected: ['mujertech', 'cascadia', 'job_target']
    manual_tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )  # user overrides

    # Message stats (derived from messages table)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    last_message_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_message_direction: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # 'sent' or 'received'

    # Record timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="contact", cascade="all, delete-orphan"
    )
    resurrection_opportunities: Mapped[list["ResurrectionOpportunity"]] = relationship(
        "ResurrectionOpportunity", back_populates="contact", cascade="all, delete-orphan"
    )
    outreach_queue_items: Mapped[list["OutreachQueueItem"]] = relationship(
        "OutreachQueueItem", back_populates="contact", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contact {self.name} ({self.linkedin_url})>"
