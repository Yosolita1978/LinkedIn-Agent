"""
Follower connection schemas — request/response models for the follower connector.
"""

from typing import Optional

from pydantic import BaseModel, Field


class FollowerCandidate(BaseModel):
    """A follower who matched a segment and is a candidate for connection."""
    name: str
    headline: str = ""
    profile_url: str
    location: str = ""
    company: str = ""
    about: str = ""
    segments: list[str]


class ScanRequest(BaseModel):
    """Parameters for the follower scan."""
    max_followers: int = Field(50, ge=1, le=200, description="Max followers to scrape from the list")
    max_profiles: int = Field(15, ge=1, le=50, description="Max profiles to enrich (limits scraping time)")


class ScanStats(BaseModel):
    followers_scraped: int = 0
    already_in_db: int = 0
    profiles_enriched: int = 0
    profiles_failed: int = 0
    matched_mujertech: int = 0
    matched_cascadia: int = 0
    matched_job_target: int = 0
    no_segment: int = 0


class ScanResponse(BaseModel):
    candidates: list[FollowerCandidate]
    stats: ScanStats


class GenerateNotesRequest(BaseModel):
    """Candidates to generate connection notes for."""
    candidates: list[FollowerCandidate]


class CandidateWithNote(BaseModel):
    """A candidate with a generated connection note for user review."""
    name: str
    headline: str = ""
    profile_url: str
    location: str = ""
    company: str = ""
    about: str = ""
    segments: list[str]
    note: str = ""


class GenerateNotesResponse(BaseModel):
    candidates: list[CandidateWithNote]


class ConnectRequest(BaseModel):
    """Approved candidates with user-reviewed notes to send."""
    candidates: list[CandidateWithNote]
    max_connections: int = Field(10, ge=1, le=25, description="Max requests per run")


class ConnectResult(BaseModel):
    """Result of a single connection request."""
    success: bool
    status: str  # sent, already_connected, already_pending, failed, note_not_supported
    profile_url: str
    error: Optional[str] = None
    name: str = ""
    segments: list[str] = []
    note_sent: str = ""
    note_for_manual: str = ""


class ConnectStats(BaseModel):
    total: int = 0
    sent: int = 0
    already_connected: int = 0
    already_pending: int = 0
    failed: int = 0
    note_not_supported: int = 0


class ConnectResponse(BaseModel):
    results: list[ConnectResult]
    stats: ConnectStats
