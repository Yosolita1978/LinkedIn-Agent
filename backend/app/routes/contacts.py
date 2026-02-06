"""
Contacts routes - view and manage contacts with warmth scores.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Contact, ResurrectionOpportunity
from app.schemas.contact import (
    ContactResponse,
    ContactListResponse,
    ContactDetailResponse,
    ContactUpdate,
    WarmthBreakdown,
    MessageMetadata,
    ResurrectionOpportunitySummary,
)
from app.services.warmth_scorer import recalculate_warmth_for_contacts_with_messages
from app.services.segmenter import segment_all_contacts, segment_contacts_without_tags

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    warmth_min: Optional[int] = Query(None, ge=0, le=100),
    warmth_max: Optional[int] = Query(None, ge=0, le=100),
    has_messages: Optional[bool] = None,
    segment: Optional[str] = None,
    sort_by: str = Query("warmth", regex="^(warmth|name|last_message|total_messages)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    """
    List contacts with pagination and filtering.
    """
    # Base query
    stmt = select(Contact)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Contact.name.ilike(search_pattern),
                Contact.company.ilike(search_pattern),
                Contact.headline.ilike(search_pattern),
            )
        )

    if warmth_min is not None:
        stmt = stmt.where(Contact.warmth_score >= warmth_min)

    if warmth_max is not None:
        stmt = stmt.where(Contact.warmth_score <= warmth_max)

    if has_messages is True:
        stmt = stmt.where(Contact.total_messages > 0)
    elif has_messages is False:
        stmt = stmt.where(Contact.total_messages == 0)

    if segment:
        stmt = stmt.where(Contact.segment_tags.contains([segment]))

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply sorting
    if sort_by == "warmth":
        order_col = Contact.warmth_score
    elif sort_by == "name":
        order_col = Contact.name
    elif sort_by == "last_message":
        order_col = Contact.last_message_date
    else:  # total_messages
        order_col = Contact.total_messages

    if sort_order == "desc":
        stmt = stmt.order_by(order_col.desc().nulls_last())
    else:
        stmt = stmt.order_by(order_col.asc().nulls_last())

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    contacts = result.scalars().all()

    return ContactListResponse(
        contacts=[ContactResponse.model_validate(c) for c in contacts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/top-warmth")
async def get_top_warmth_contacts(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get contacts with highest warmth scores.
    Quick endpoint for dashboard.
    """
    stmt = (
        select(Contact)
        .where(Contact.warmth_score > 0)
        .order_by(Contact.warmth_score.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    contacts = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "name": c.name,
            "company": c.company,
            "headline": c.headline,
            "warmth_score": c.warmth_score,
            "warmth_breakdown": c.warmth_breakdown,
            "total_messages": c.total_messages,
            "last_message_date": c.last_message_date,
        }
        for c in contacts
    ]


@router.get("/stats")
async def get_contact_stats(db: AsyncSession = Depends(get_db)):
    """
    Get overall contact statistics.
    """
    # Total contacts
    total_result = await db.execute(select(func.count(Contact.id)))
    total_contacts = total_result.scalar() or 0

    # Contacts with messages
    with_messages_result = await db.execute(
        select(func.count(Contact.id)).where(Contact.total_messages > 0)
    )
    contacts_with_messages = with_messages_result.scalar() or 0

    # Warmth distribution
    warmth_buckets = {
        "hot": 0,      # 70-100
        "warm": 0,     # 40-69
        "cool": 0,     # 10-39
        "cold": 0,     # 1-9
        "none": 0,     # 0 or null
    }

    bucket_queries = [
        ("hot", Contact.warmth_score >= 70),
        ("warm", (Contact.warmth_score >= 40) & (Contact.warmth_score < 70)),
        ("cool", (Contact.warmth_score >= 10) & (Contact.warmth_score < 40)),
        ("cold", (Contact.warmth_score >= 1) & (Contact.warmth_score < 10)),
    ]

    for bucket_name, condition in bucket_queries:
        result = await db.execute(
            select(func.count(Contact.id)).where(condition)
        )
        warmth_buckets[bucket_name] = result.scalar() or 0

    warmth_buckets["none"] = total_contacts - sum(
        warmth_buckets[k] for k in ["hot", "warm", "cool", "cold"]
    )

    # Average warmth for contacts with messages
    avg_result = await db.execute(
        select(func.avg(Contact.warmth_score)).where(Contact.warmth_score > 0)
    )
    avg_warmth = avg_result.scalar()

    return {
        "total_contacts": total_contacts,
        "contacts_with_messages": contacts_with_messages,
        "contacts_without_messages": total_contacts - contacts_with_messages,
        "warmth_distribution": warmth_buckets,
        "average_warmth": round(avg_warmth, 1) if avg_warmth else 0,
    }


@router.get("/{contact_id}", response_model=ContactDetailResponse)
async def get_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed contact information including warmth breakdown.
    """
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get resurrection opportunities
    resurrection_stmt = (
        select(ResurrectionOpportunity)
        .where(ResurrectionOpportunity.contact_id == contact_id)
        .where(ResurrectionOpportunity.is_active == True)
    )
    resurrection_result = await db.execute(resurrection_stmt)
    resurrections = resurrection_result.scalars().all()

    # Build response
    response_data = {
        "id": contact.id,
        "linkedin_url": contact.linkedin_url,
        "name": contact.name,
        "headline": contact.headline,
        "location": contact.location,
        "company": contact.company,
        "position": contact.position,
        "about": contact.about,
        "email": contact.email,
        "experience": contact.experience,
        "education": contact.education,
        "connection_date": contact.connection_date,
        "scraped_at": contact.scraped_at,
        "warmth_score": contact.warmth_score,
        "warmth_breakdown": WarmthBreakdown(**contact.warmth_breakdown) if contact.warmth_breakdown else None,
        "warmth_calculated_at": contact.warmth_calculated_at,
        "segment_tags": contact.segment_tags,
        "manual_tags": contact.manual_tags,
        "message_metadata": MessageMetadata(
            total_messages=contact.total_messages,
            last_message_date=contact.last_message_date,
            last_message_direction=contact.last_message_direction,
        ) if contact.total_messages > 0 else None,
        "resurrection_opportunities": [
            ResurrectionOpportunitySummary.model_validate(r) for r in resurrections
        ],
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
    }

    return ContactDetailResponse(**response_data)


@router.patch("/{contact_id}/tags")
async def update_contact_tags(
    contact_id: UUID,
    update: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a contact's manual tags.
    """
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if update.manual_tags is not None:
        contact.manual_tags = update.manual_tags

    await db.commit()

    return {"status": "updated", "manual_tags": contact.manual_tags}


@router.post("/recalculate-warmth")
async def recalculate_warmth(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger warmth score recalculation for all contacts with messages.
    """
    result = await recalculate_warmth_for_contacts_with_messages(db)

    return {
        "status": "completed",
        "contacts_processed": result["contacts_processed"],
    }


@router.post("/segment")
async def run_segmentation(
    db: AsyncSession = Depends(get_db),
    all_contacts: bool = Query(False, description="Re-segment all contacts, not just untagged"),
):
    """
    Run audience segmentation on contacts.

    By default, only segments contacts without existing tags (incremental).
    Set all_contacts=true to re-segment everyone.
    """
    if all_contacts:
        result = await segment_all_contacts(db)
    else:
        result = await segment_contacts_without_tags(db)

    return {
        "status": "completed",
        "contacts_processed": result["contacts_processed"],
        "segments": {
            "mujertech": result["mujertech_count"],
            "cascadia": result["cascadia_count"],
            "job_target": result["job_target_count"],
        },
        "no_segment": result["no_segment_count"],
    }
