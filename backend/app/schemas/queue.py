from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OutreachQueueItemBase(BaseModel):
    use_case: str  # 'mujertech', 'cascadia', 'job_search'
    outreach_type: str  # 'resurrection', 'warm', 'cold'
    generated_message: Optional[str] = None


class OutreachQueueItemCreate(OutreachQueueItemBase):
    contact_id: UUID


class OutreachQueueItemUpdate(BaseModel):
    status: Optional[str] = None  # 'queued', 'sent', 'replied'
    generated_message: Optional[str] = None


class OutreachQueueItemResponse(BaseModel):
    id: UUID
    contact_id: UUID
    use_case: str
    outreach_type: str
    generated_message: Optional[str] = None
    status: str
    created_at: datetime
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
