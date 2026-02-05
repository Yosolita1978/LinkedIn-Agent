from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TargetCompanyBase(BaseModel):
    name: str
    notes: Optional[str] = None


class TargetCompanyCreate(TargetCompanyBase):
    pass


class TargetCompanyUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None


class TargetCompanyResponse(BaseModel):
    id: UUID
    name: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TargetCompanyWithContacts(TargetCompanyResponse):
    contact_count: int = 0
