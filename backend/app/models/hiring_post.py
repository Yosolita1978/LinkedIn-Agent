import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HiringPost(Base):
    """
    A LinkedIn post found by a content search (e.g. "forward deployed engineer hiring").

    LinkedIn's search page has no post permalinks, so posts are deduped by a
    fingerprint (author + start of the text). Re-running a search only adds new
    posts and keeps your status and notes.
    """

    __tablename__ = "hiring_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # sha1 of author + first 300 chars of the post text. The only dedup key.
    fingerprint: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )

    author_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author_degree: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 1st, 2nd, 3rd+
    author_headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # empty for some group posts
    group_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # set when posted in a group

    post_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # The job attached to the post, if any. Also saved to job_opportunities.
    job_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # As shown when first found, e.g. "15h" or "2d".
    posted_ago: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # The search keywords that first found this post.
    search_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle: new → interested → contacted | skipped
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<HiringPost {self.author_name} ({self.status})>"
