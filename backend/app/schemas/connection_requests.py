"""
Connection request schemas — for tracking and querying past connection requests.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConnectionRequestOut(BaseModel):
    """A single connection request record."""
    id: str
    profile_url: str
    name: str
    headline: str | None = None
    company: str | None = None
    location: str | None = None
    segments: list[str] | None = None
    note_sent: str | None = None
    status: str
    sent_at: datetime
    accepted_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConnectionRequestListResponse(BaseModel):
    """Response for listing connection requests."""
    requests: list[ConnectionRequestOut]
    total: int


class CheckAcceptancesResponse(BaseModel):
    """Response from checking which pending requests were accepted."""
    checked: int
    newly_accepted: int
    still_pending: int
    accepted_names: list[str]


class SegmentAcceptanceStats(BaseModel):
    """Acceptance stats for a single segment."""
    segment: str
    total_sent: int
    accepted: int
    pending: int
    failed: int
    acceptance_rate: float


class ConnectionRequestStatsResponse(BaseModel):
    """Overall connection request stats."""
    total_requests: int
    total_accepted: int
    total_pending: int
    total_failed: int
    overall_acceptance_rate: float
    by_segment: list[SegmentAcceptanceStats]
