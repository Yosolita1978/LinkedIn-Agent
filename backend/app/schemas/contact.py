from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class WarmthBreakdown(BaseModel):
    recency: int = 0  # 0-30
    frequency: int = 0  # 0-20
    depth: int = 0  # 0-25
    responsiveness: int = 0  # 0-15
    initiation: int = 0  # 0-10


class ContactBase(BaseModel):
    linkedin_url: str
    name: str
    headline: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    about: Optional[str] = None
    email: Optional[str] = None


class ContactCreate(ContactBase):
    experience: Optional[list[dict]] = None
    education: Optional[list[dict]] = None
    connection_date: Optional[date] = None


class ContactUpdate(BaseModel):
    headline: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    about: Optional[str] = None
    email: Optional[str] = None
    experience: Optional[list[dict]] = None
    education: Optional[list[dict]] = None
    manual_tags: Optional[list[str]] = None


class ContactResponse(BaseModel):
    id: UUID
    linkedin_url: str
    name: str
    headline: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    warmth_score: Optional[int] = None
    segment_tags: Optional[list[str]] = None
    manual_tags: Optional[list[str]] = None
    last_message_date: Optional[date] = None
    last_message_direction: Optional[str] = None
    total_messages: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    contacts: list[ContactResponse]
    total: int
    page: int
    page_size: int


class ResurrectionOpportunitySummary(BaseModel):
    id: UUID
    hook_type: str
    hook_detail: Optional[str] = None
    detected_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class MessageMetadata(BaseModel):
    total_messages: int
    first_message_date: Optional[datetime] = None
    last_message_date: Optional[datetime] = None
    last_message_direction: Optional[str] = None
    messages_sent: int = 0
    messages_received: int = 0


class ContactDetailResponse(BaseModel):
    id: UUID
    linkedin_url: str
    name: str
    headline: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    about: Optional[str] = None
    email: Optional[str] = None
    experience: Optional[list[dict]] = None
    education: Optional[list[dict]] = None
    connection_date: Optional[date] = None
    scraped_at: Optional[datetime] = None

    # Warmth
    warmth_score: Optional[int] = None
    warmth_breakdown: Optional[WarmthBreakdown] = None
    warmth_calculated_at: Optional[datetime] = None

    # Segmentation
    segment_tags: Optional[list[str]] = None
    manual_tags: Optional[list[str]] = None

    # Message metadata (not content)
    message_metadata: Optional[MessageMetadata] = None

    # Resurrection opportunities
    resurrection_opportunities: list[ResurrectionOpportunitySummary] = []

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
