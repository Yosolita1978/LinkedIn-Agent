"""
Ranking routes - daily outreach recommendations based on priority scoring.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.ranking_service import get_daily_recommendations, get_contact_priority


router = APIRouter(prefix="/api/ranking", tags=["ranking"])


@router.get("/recommendations")
async def list_recommendations(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(15, ge=1, le=50),
    segment: Optional[str] = Query(None, description="Filter by segment: mujertech, cascadia, job_target"),
):
    """
    Get today's outreach recommendations, ranked by priority score.

    Priority = warmth (40%) + segment relevance (25%) + urgency (35%).
    Excludes contacts already in the outreach queue (draft/approved).
    """
    valid_segments = ["mujertech", "cascadia", "job_target"]

    if segment and segment not in valid_segments:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid segment. Options: {', '.join(valid_segments)}",
        )

    return await get_daily_recommendations(db, limit, segment)


@router.get("/recommendations/{contact_id}")
async def contact_priority(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get priority breakdown for a specific contact.
    """
    result = await get_contact_priority(db, contact_id)

    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")

    return result
