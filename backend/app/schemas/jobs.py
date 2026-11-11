from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


VALID_JOB_STATUSES = ["new", "interested", "applied", "skipped"]

# Each phrase is one browser search (~15-30s), so the default run stays small.
# The career skill has the full keyword bank and picks 1-3 phrases per run.
DEFAULT_JOB_KEYWORDS = [
    "AI Agent Engineer",
    "AI Agent Consultant",
    "AI Educator",
    "Technical Enablement",
]

MAX_DESCRIPTION_CHARS = 15000


class JobSearchRequest(BaseModel):
    keywords: list[str] = Field(
        default_factory=lambda: list(DEFAULT_JOB_KEYWORDS),
        description="One LinkedIn Jobs search per keyword phrase",
    )
    location: str = Field("United States", description="LinkedIn location text, e.g. 'Seattle, Washington'")
    remote_only: bool = Field(False, description="Only remote jobs")
    posted_within_days: Optional[int] = Field(
        7, ge=1, le=30, description="Only jobs posted in the last N days (None = any time)"
    )
    max_per_keyword: int = Field(25, ge=1, le=50, description="Max jobs to collect per keyword")


class JobOut(BaseModel):
    id: UUID
    linkedin_job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_url: str
    card_text: Optional[str] = None
    search_keywords: Optional[str] = None
    status: str
    notes: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    details_fetched_at: Optional[datetime] = None  # set once the full posting is saved

    model_config = {"from_attributes": True}


class JobPersonOut(BaseModel):
    id: UUID
    source: str                         # reach_out, hiring_team, company_page, network_hint
    name: str                           # for network_hint: the summary line itself
    degree: Optional[str] = None        # 1st, 2nd, 3rd+
    headline: Optional[str] = None
    profile_url: Optional[str] = None
    reason: Optional[str] = None        # e.g. "School alum from University of Washington"
    contact_id: Optional[UUID] = None   # set when this person is already in your contacts
    found_at: datetime

    model_config = {"from_attributes": True}


class JobDetailOut(JobOut):
    # Kept out of JobOut so job lists stay small; up to 15,000 chars each.
    description: Optional[str] = None
    # People LinkedIn shows on the job page (saved when details are fetched).
    people: list[JobPersonOut] = []


class JobDetailsRequest(BaseModel):
    job_ids: list[UUID] = Field(min_length=1, max_length=10)
    refresh: bool = Field(False, description="Re-fetch even if the posting is already saved")


class JobDetailsResponse(BaseModel):
    jobs: list[JobDetailOut]
    fetched_count: int = 0                # jobs whose page was opened this run
    closed_job_ids: list[UUID] = []       # postings that say "No longer accepting applications"
    errors: list[str] = []                # per-job errors (the other jobs still run)


class JobPeopleScanResponse(BaseModel):
    job: JobDetailOut                          # the job with all its people
    company_people_url: Optional[str] = None   # the People page that was read
    company_people_count: int = 0              # 1st/2nd-degree people saved from it
    errors: list[str] = []


class JobSearchResponse(BaseModel):
    jobs: list[JobOut]           # every job seen in this search (new + already saved)
    new_count: int = 0           # jobs saved for the first time
    already_saved_count: int = 0 # jobs that were already in the table
    errors: list[str] = []       # per-keyword errors (the other keywords still run)


class JobListResponse(BaseModel):
    jobs: list[JobOut]
    total: int                   # rows matching the current filters
    counts: dict[str, int]       # count per status across all saved jobs


class JobUpdate(BaseModel):
    status: Optional[str] = Field(None, description="new, interested, applied, skipped")
    notes: Optional[str] = None
