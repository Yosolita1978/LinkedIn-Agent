"""
Resurrection routes - detect and manage outreach opportunities.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.resurrection_scanner import (
    run_full_scan,
    get_active_opportunities,
    dismiss_opportunity,
    scan_dormant_relationships,
    scan_broken_promises,
    scan_unanswered_questions,
    scan_they_waiting,
)


router = APIRouter(prefix="/api/resurrection", tags=["resurrection"])


@router.post("/scan")
async def trigger_scan(db: AsyncSession = Depends(get_db)):
    """
    Run all resurrection scanners to detect outreach opportunities.

    Scans for:
    - Dormant relationships (warm contacts gone quiet)
    - Broken promises (you said you'd do something)
    - Unanswered questions (they asked, you didn't respond)
    - They're waiting (ball is in your court)
    """
    result = await run_full_scan(db)
    return result


@router.post("/scan/{scan_type}")
async def trigger_specific_scan(
    scan_type: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Run a specific resurrection scanner.

    scan_type options: dormant, promises, questions, waiting
    """
    scanners = {
        "dormant": scan_dormant_relationships,
        "promises": scan_broken_promises,
        "questions": scan_unanswered_questions,
        "waiting": scan_they_waiting,
    }

    if scan_type not in scanners:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scan type. Options: {', '.join(scanners.keys())}",
        )

    result = await scanners[scan_type](db)
    await db.commit()

    return {
        "scan_type": scan_type,
        "found": result["found"],
        "created": result["created"],
        "updated": result["updated"],
    }


@router.get("/opportunities")
async def list_opportunities(
    db: AsyncSession = Depends(get_db),
    hook_type: Optional[str] = Query(
        None,
        description="Filter by type: dormant, promise_made, question_unanswered, they_waiting",
    ),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get active resurrection opportunities.

    Returns opportunities sorted by contact warmth score.
    """
    valid_types = ["dormant", "promise_made", "question_unanswered", "they_waiting"]

    if hook_type and hook_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid hook_type. Options: {', '.join(valid_types)}",
        )

    opportunities = await get_active_opportunities(db, hook_type, limit)

    return {
        "count": len(opportunities),
        "opportunities": opportunities,
    }


@router.post("/opportunities/{opportunity_id}/dismiss")
async def dismiss_resurrection_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an opportunity as addressed/dismissed.
    """
    success = await dismiss_opportunity(db, str(opportunity_id))

    if not success:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return {"status": "dismissed", "id": str(opportunity_id)}
