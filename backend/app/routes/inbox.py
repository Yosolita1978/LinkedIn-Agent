"""
Inbox routes — sync and browse LinkedIn conversations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.inbox import (
    InboxListResponse,
    InboxConversationDetail,
    InboxSyncResponse,
    InboxStatsResponse,
)
from app.services import inbox_service


router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.post("/sync", response_model=InboxSyncResponse)
async def sync_inbox(
    limit: int = Query(40, ge=1, le=100, description="Number of conversations to fetch"),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync recent LinkedIn conversations via Playwright browser automation.

    Scrapes the messaging page, matches participants to existing contacts,
    and imports new messages. Updates needs_reply status.

    Note: This opens a headless browser — may take 15-30 seconds.
    """
    try:
        result = await inbox_service.sync_conversations(db, limit=limit)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=InboxListResponse)
async def list_inbox(
    filter: Optional[str] = Query(None, description="Filter: needs_reply, waiting"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List inbox conversations grouped by contact.

    Filters:
    - needs_reply: contacts whose last message is from them
    - waiting: contacts whose last message is from you
    """
    if filter and filter not in ("needs_reply", "waiting"):
        raise HTTPException(status_code=400, detail="Invalid filter. Options: needs_reply, waiting")

    conversations, total = await inbox_service.get_inbox(
        db, filter_type=filter, limit=limit, offset=offset
    )
    return {"conversations": conversations, "total": total}


@router.get("/stats", response_model=InboxStatsResponse)
async def inbox_stats(db: AsyncSession = Depends(get_db)):
    """Get inbox summary: total conversations, needs reply, waiting for them."""
    return await inbox_service.get_inbox_stats(db)


@router.get("/{contact_id}", response_model=InboxConversationDetail)
async def get_conversation(
    contact_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get full message thread with a specific contact."""
    messages = await inbox_service.get_conversation_messages(db, contact_id, limit=limit)
    return {"contact_id": contact_id, "messages": messages}
