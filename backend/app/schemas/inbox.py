from typing import Optional

from pydantic import BaseModel


class InboxConversation(BaseModel):
    contact_id: str
    contact_name: str
    contact_company: Optional[str] = None
    contact_headline: Optional[str] = None
    contact_linkedin_url: Optional[str] = None
    warmth_score: Optional[int] = None
    last_message_date: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_direction: Optional[str] = None
    total_messages: int = 0
    needs_reply: bool = False


class InboxListResponse(BaseModel):
    conversations: list[InboxConversation]
    total: int


class InboxMessage(BaseModel):
    id: str
    direction: str
    date: str
    content: Optional[str] = None
    content_length: Optional[int] = None
    is_substantive: Optional[bool] = None
    conversation_id: Optional[str] = None
    synced_at: Optional[str] = None


class InboxConversationDetail(BaseModel):
    contact_id: str
    messages: list[InboxMessage]


class InboxSyncResponse(BaseModel):
    conversations_fetched: int
    conversations_synced: int
    new_messages: int
    skipped_no_contact: int


class InboxStatsResponse(BaseModel):
    total_conversations: int
    needs_reply: int
    waiting_for_them: int
