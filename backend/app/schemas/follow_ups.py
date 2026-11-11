from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


VALID_STAGES = [
    "requested",       # connection request sent
    "connected",       # accepted, nothing exchanged yet
    "talking",         # messages going back and forth
    "call_scheduled",
    "interviewing",
    "no_response",     # gave up for now; revisit later
    "closed",          # finished (hired, rejected, not interested) → status becomes done
]
VALID_STATUSES = ["open", "done"]


class HistoryEntry(BaseModel):
    at: datetime
    summary: str
    stage: Optional[str] = None


class FollowUpCreate(BaseModel):
    name: str = Field(min_length=1)
    profile_url: Optional[str] = None
    company: Optional[str] = None
    job_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    stage: str = "requested"
    last_touch: Optional[str] = Field(None, description="What just happened, e.g. 'Sent connection note'")
    next_action: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class FollowUpTouch(BaseModel):
    """
    Log what happened and set the next step in one call.
    next_action and due_date REPLACE the current ones (omit them = nothing scheduled).
    """
    summary: str = Field(min_length=1, description="What happened, e.g. 'He replied: sure, let's talk'")
    stage: Optional[str] = Field(None, description="New stage, if it changed")
    next_action: Optional[str] = None
    due_date: Optional[date] = None


class FollowUpUpdate(BaseModel):
    name: Optional[str] = None
    profile_url: Optional[str] = None
    company: Optional[str] = None
    job_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    next_action: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class FollowUpOut(BaseModel):
    id: UUID
    name: str
    profile_url: Optional[str] = None
    company: Optional[str] = None
    contact_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    stage: str
    status: str
    last_touch_at: Optional[datetime] = None
    last_touch: Optional[str] = None
    next_action: Optional[str] = None
    due_date: Optional[date] = None
    history: list[HistoryEntry] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FollowUpListResponse(BaseModel):
    follow_ups: list[FollowUpOut]
    total: int                   # rows matching the current filters
    overdue_count: int           # open follow-ups with a due date before today
    due_today_count: int         # open follow-ups due today
    stage_counts: dict[str, int] # open follow-ups per stage
