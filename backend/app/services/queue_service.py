"""
Queue Service

Manages the outreach queue workflow:
- Add generated messages to queue (as drafts)
- Transition status: draft → approved → sent → responded
- Prevent duplicate active outreach to the same contact
- Query and filter queue items
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutreachQueueItem, Contact


# Valid status transitions
STATUS_TRANSITIONS = {
    "draft": ["approved"],
    "approved": ["sent", "draft"],       # can go back to draft
    "sent": ["responded"],
    "responded": [],                      # terminal state
}


async def check_duplicate(
    db: AsyncSession,
    contact_id: UUID,
) -> Optional[OutreachQueueItem]:
    """
    Check if the contact already has an active queue item (draft or approved).
    Returns the existing item if found, None otherwise.
    """
    stmt = select(OutreachQueueItem).where(
        OutreachQueueItem.contact_id == contact_id,
        OutreachQueueItem.status.in_(["draft", "approved"]),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def add_to_queue(
    db: AsyncSession,
    contact_id: UUID,
    use_case: str,
    outreach_type: str,
    purpose: str,
    generated_message: Optional[str] = None,
) -> OutreachQueueItem:
    """
    Add a message to the outreach queue as a draft.
    Raises ValueError if the contact already has an active queue item.
    """
    # Check for duplicates
    existing = await check_duplicate(db, contact_id)
    if existing:
        raise ValueError(
            f"Contact already has an active queue item (status: {existing.status}). "
            f"Queue item ID: {existing.id}"
        )

    item = OutreachQueueItem(
        contact_id=contact_id,
        use_case=use_case,
        outreach_type=outreach_type,
        purpose=purpose,
        generated_message=generated_message,
        status="draft",
    )

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_status(
    db: AsyncSession,
    item_id: UUID,
    new_status: str,
) -> OutreachQueueItem:
    """
    Transition a queue item to a new status.
    Validates the transition is allowed and sets timestamps.
    """
    stmt = select(OutreachQueueItem).where(OutreachQueueItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise ValueError(f"Queue item not found: {item_id}")

    allowed = STATUS_TRANSITIONS.get(item.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{item.status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    item.status = new_status

    # Set timestamps based on the transition
    now = datetime.utcnow()
    if new_status == "approved":
        item.approved_at = now
    elif new_status == "sent":
        item.sent_at = now
    elif new_status == "responded":
        item.replied_at = now

    await db.commit()
    await db.refresh(item)
    return item


async def update_message(
    db: AsyncSession,
    item_id: UUID,
    generated_message: str,
) -> OutreachQueueItem:
    """
    Update the message text for a draft queue item.
    Only drafts can be edited.
    """
    stmt = select(OutreachQueueItem).where(OutreachQueueItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise ValueError(f"Queue item not found: {item_id}")

    if item.status != "draft":
        raise ValueError(f"Can only edit drafts. Current status: {item.status}")

    item.generated_message = generated_message
    await db.commit()
    await db.refresh(item)
    return item


async def get_queue_item(
    db: AsyncSession,
    item_id: UUID,
) -> Optional[OutreachQueueItem]:
    """Get a single queue item by ID."""
    stmt = select(OutreachQueueItem).where(OutreachQueueItem.id == item_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_queue_items(
    db: AsyncSession,
    status: Optional[str] = None,
    use_case: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    List queue items with optional filtering.
    Returns items with contact info and total count.
    """
    # Base query with contact join
    stmt = (
        select(
            OutreachQueueItem,
            Contact.name.label("contact_name"),
            Contact.headline.label("contact_headline"),
            Contact.company.label("contact_company"),
        )
        .join(Contact, OutreachQueueItem.contact_id == Contact.id)
    )

    # Count query
    count_stmt = select(func.count(OutreachQueueItem.id))

    # Apply filters
    if status:
        stmt = stmt.where(OutreachQueueItem.status == status)
        count_stmt = count_stmt.where(OutreachQueueItem.status == status)

    if use_case:
        stmt = stmt.where(OutreachQueueItem.use_case == use_case)
        count_stmt = count_stmt.where(OutreachQueueItem.use_case == use_case)

    # Get total count
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Get items ordered by most recent first
    stmt = stmt.order_by(OutreachQueueItem.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        queue_item = row[0]
        items.append({
            "id": queue_item.id,
            "contact_id": queue_item.contact_id,
            "use_case": queue_item.use_case,
            "outreach_type": queue_item.outreach_type,
            "purpose": queue_item.purpose,
            "generated_message": queue_item.generated_message,
            "status": queue_item.status,
            "created_at": queue_item.created_at,
            "approved_at": queue_item.approved_at,
            "sent_at": queue_item.sent_at,
            "replied_at": queue_item.replied_at,
            "contact_name": row[1],
            "contact_headline": row[2],
            "contact_company": row[3],
        })

    return items, total


async def delete_queue_item(
    db: AsyncSession,
    item_id: UUID,
) -> bool:
    """
    Delete a queue item. Only drafts and approved items can be deleted.
    Sent/responded items are kept for history.
    """
    stmt = select(OutreachQueueItem).where(OutreachQueueItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise ValueError(f"Queue item not found: {item_id}")

    if item.status in ["sent", "responded"]:
        raise ValueError(
            f"Cannot delete items with status '{item.status}'. "
            f"Sent and responded items are kept for history."
        )

    await db.delete(item)
    await db.commit()
    return True


async def get_queue_stats(db: AsyncSession) -> dict:
    """Get queue statistics: counts by status and use_case."""
    # Count by status
    status_stmt = (
        select(OutreachQueueItem.status, func.count(OutreachQueueItem.id))
        .group_by(OutreachQueueItem.status)
    )
    status_result = await db.execute(status_stmt)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Count by use_case
    use_case_stmt = (
        select(OutreachQueueItem.use_case, func.count(OutreachQueueItem.id))
        .group_by(OutreachQueueItem.use_case)
    )
    use_case_result = await db.execute(use_case_stmt)
    by_use_case = {row[0]: row[1] for row in use_case_result.all()}

    total = sum(by_status.values())

    return {
        "total": total,
        "by_status": by_status,
        "by_use_case": by_use_case,
    }
