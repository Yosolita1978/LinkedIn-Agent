"""
Outreach Queue routes — manage the message workflow.

Workflow: draft → approved → sent → responded
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.queue import (
    OutreachQueueItemCreate,
    OutreachQueueItemUpdate,
    StatusUpdate,
    OutreachQueueItemResponse,
    QueueListResponse,
    QueueStatsResponse,
    VALID_STATUSES,
    VALID_USE_CASES,
    VALID_OUTREACH_TYPES,
    VALID_PURPOSES,
)
from app.services import queue_service


router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.post("/", response_model=OutreachQueueItemResponse)
async def add_to_queue(
    request: OutreachQueueItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a message to the outreach queue as a draft.

    Validates inputs and prevents duplicate active outreach
    to the same contact (only one draft/approved item per contact).
    """
    if request.use_case not in VALID_USE_CASES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid use_case. Options: {', '.join(VALID_USE_CASES)}",
        )

    if request.outreach_type not in VALID_OUTREACH_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outreach_type. Options: {', '.join(VALID_OUTREACH_TYPES)}",
        )

    if request.purpose not in VALID_PURPOSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose. Options: {', '.join(VALID_PURPOSES)}",
        )

    try:
        item = await queue_service.add_to_queue(
            db=db,
            contact_id=request.contact_id,
            use_case=request.use_case,
            outreach_type=request.outreach_type,
            purpose=request.purpose,
            generated_message=request.generated_message,
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/", response_model=QueueListResponse)
async def list_queue(
    status: Optional[str] = Query(None, description="Filter by status: draft, approved, sent, responded"),
    use_case: Optional[str] = Query(None, description="Filter by use_case: mujertech, cascadia, job_search"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List queue items with optional filtering by status and use_case.

    Returns items with contact info, ordered by most recent first.
    """
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Options: {', '.join(VALID_STATUSES)}",
        )

    if use_case and use_case not in VALID_USE_CASES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid use_case. Options: {', '.join(VALID_USE_CASES)}",
        )

    items, total = await queue_service.list_queue_items(
        db=db,
        status=status,
        use_case=use_case,
        limit=limit,
        offset=offset,
    )

    return {"items": items, "total": total}


@router.get("/stats", response_model=QueueStatsResponse)
async def queue_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get queue statistics: counts by status and use_case."""
    return await queue_service.get_queue_stats(db)


@router.get("/{item_id}", response_model=OutreachQueueItemResponse)
async def get_queue_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single queue item by ID."""
    item = await queue_service.get_queue_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.patch("/{item_id}/status", response_model=OutreachQueueItemResponse)
async def update_queue_status(
    item_id: UUID,
    request: StatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Transition a queue item to a new status.

    Valid transitions:
    - draft → approved
    - approved → sent (or back to draft)
    - sent → responded
    """
    if request.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Options: {', '.join(VALID_STATUSES)}",
        )

    try:
        item = await queue_service.update_status(db, item_id, request.status)
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{item_id}/message", response_model=OutreachQueueItemResponse)
async def update_queue_message(
    item_id: UUID,
    request: OutreachQueueItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update the message text for a draft queue item.
    Only items with status 'draft' can be edited.
    """
    if not request.generated_message:
        raise HTTPException(status_code=400, detail="generated_message is required")

    try:
        item = await queue_service.update_message(db, item_id, request.generated_message)
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{item_id}")
async def delete_queue_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a queue item.
    Only draft and approved items can be deleted.
    Sent/responded items are kept for history.
    """
    try:
        await queue_service.delete_queue_item(db, item_id)
        return {"detail": "Queue item deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
