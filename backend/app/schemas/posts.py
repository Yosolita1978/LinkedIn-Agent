from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


VALID_POST_STATUSES = ["new", "interested", "contacted", "skipped"]

# Each phrase is one browser search (~20-40s). The career skill has the full
# keyword bank and picks 1-3 phrases per run.
DEFAULT_POST_KEYWORDS = [
    "forward deployed engineer hiring",
    "AI agent engineer hiring",
    "AI enablement hiring",
    "AI educator hiring",
]

MAX_POST_TEXT_CHARS = 8000

DatePosted = Literal["past-24h", "past-week", "past-month"]


class PostSearchRequest(BaseModel):
    keywords: list[str] = Field(
        default_factory=lambda: list(DEFAULT_POST_KEYWORDS),
        description="One LinkedIn posts search per keyword phrase",
    )
    date_posted: DatePosted = Field("past-24h", description="LinkedIn's 'Date posted' filter")
    max_per_keyword: int = Field(20, ge=1, le=50, description="Max posts to collect per keyword")


class PostOut(BaseModel):
    id: UUID
    author_name: str
    author_degree: Optional[str] = None
    author_headline: Optional[str] = None
    author_url: Optional[str] = None
    group_name: Optional[str] = None
    post_text: str
    job_url: Optional[str] = None
    posted_ago: Optional[str] = None
    search_keywords: Optional[str] = None
    status: str
    notes: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class PostSearchResponse(BaseModel):
    posts: list[PostOut]          # every post seen in this search (new + already saved)
    new_count: int = 0            # posts saved for the first time
    already_saved_count: int = 0  # posts that were already in the table
    new_jobs_count: int = 0       # attached jobs added to job_opportunities
    errors: list[str] = []        # per-keyword errors (the other keywords still run)


class PostListResponse(BaseModel):
    posts: list[PostOut]
    total: int                    # rows matching the current filters
    counts: dict[str, int]        # count per status across all saved posts


class PostUpdate(BaseModel):
    status: Optional[str] = Field(None, description="new, interested, contacted, skipped")
    notes: Optional[str] = None
