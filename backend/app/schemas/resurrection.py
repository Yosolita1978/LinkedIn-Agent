from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ResurrectionOpportunityBase(BaseModel):
    hook_type: str  # 'dormant', 'promise_made', 'question_unanswered', 'they_waiting'
    hook_detail: Optional[str] = None


class ResurrectionOpportunityCreate(ResurrectionOpportunityBase):
    contact_id: UUID
    source_message_id: Optional[UUID] = None


class ResurrectionOpportunityResponse(BaseModel):
    id: UUID
    contact_id: UUID
    hook_type: str
    hook_detail: Optional[str] = None
    source_message_id: Optional[UUID] = None
    detected_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ResurrectionOpportunityWithContact(ResurrectionOpportunityResponse):
    contact_name: str
    contact_headline: Optional[str] = None
    contact_company: Optional[str] = None
    warmth_score: Optional[int] = None
