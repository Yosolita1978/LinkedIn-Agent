from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MessageBase(BaseModel):
    direction: str  # 'sent' or 'received'
    date: datetime
    subject: Optional[str] = None
    content: Optional[str] = None


class MessageCreate(MessageBase):
    contact_id: UUID
    conversation_id: Optional[str] = None
    content_length: Optional[int] = None
    is_substantive: Optional[bool] = None


class MessageResponse(BaseModel):
    id: UUID
    contact_id: UUID
    direction: str
    date: datetime
    subject: Optional[str] = None
    content_length: Optional[int] = None
    is_substantive: Optional[bool] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageGenerateRequest(BaseModel):
    contact_id: UUID
    use_case: str  # 'mujertech', 'cascadia', 'job_search'


class MessageRegenerateRequest(BaseModel):
    contact_id: UUID
    use_case: str
    feedback: Optional[str] = None  # User feedback for improvement


class ContactContext(BaseModel):
    name: str
    headline: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    warmth_score: Optional[int] = None
    total_messages: int = 0
    days_since_last_contact: Optional[int] = None
    last_message_direction: Optional[str] = None
    is_target_company: bool = False
    resurrection_hook: Optional[str] = None
    resurrection_detail: Optional[str] = None


class MessageGenerateResponse(BaseModel):
    outreach_type: str  # 'resurrection', 'warm', 'cold'
    message: str
    contact_context: ContactContext
    use_case: str
