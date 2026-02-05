from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DataUploadResponse(BaseModel):
    id: UUID
    file_type: str
    filename: Optional[str] = None
    records_processed: Optional[int] = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UploadResult(BaseModel):
    records_processed: int
    contacts_created: int = 0
    contacts_updated: int = 0
    messages_created: int = 0
    resurrection_found: int = 0
    errors: list[str] = []


class UploadStatusResponse(BaseModel):
    last_messages_upload: Optional[datetime] = None
    last_connections_upload: Optional[datetime] = None
    total_contacts: int = 0
    total_messages: int = 0
