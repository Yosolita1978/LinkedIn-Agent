from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


VALID_STATUSES = ["draft", "approved", "sent", "responded"]
VALID_USE_CASES = ["mujertech", "cascadia", "job_search"]
VALID_OUTREACH_TYPES = ["resurrection", "warm", "cold"]
VALID_PURPOSES = [
    "reconnect", "introduce", "follow_up", "invite_community",
    "ask_advice", "congratulate", "share_resource",
]


class OutreachQueueItemBase(BaseModel):
    use_case: str  # 'mujertech', 'cascadia', 'job_search'
    outreach_type: str  # 'resurrection', 'warm', 'cold'
    purpose: str = "reconnect"
    generated_message: Optional[str] = None


class OutreachQueueItemCreate(OutreachQueueItemBase):
    contact_id: UUID


class OutreachQueueItemUpdate(BaseModel):
    generated_message: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str = Field(description="New status: draft, approved, sent, responded")


class OutreachQueueItemResponse(BaseModel):
    id: UUID
    contact_id: UUID
    use_case: str
    outreach_type: str
    purpose: str
    generated_message: Optional[str] = None
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OutreachQueueItemWithContact(OutreachQueueItemResponse):
    contact_name: str
    contact_headline: Optional[str] = None
    contact_company: Optional[str] = None


class QueueListResponse(BaseModel):
    items: list[OutreachQueueItemWithContact]
    total: int


class QueueStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_use_case: dict[str, int]
