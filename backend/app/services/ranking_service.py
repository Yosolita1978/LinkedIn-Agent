"""
Contact Ranking Service

Computes a priority score (0-100) for each contact by combining:
- Warmth score (40%): relationship strength
- Segment relevance (25%): alignment with outreach goals
- Urgency (35%): active resurrection opportunity hooks

Returns ranked recommendations for daily outreach.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, ResurrectionOpportunity, OutreachQueueItem


# Weights for the composite priority score
WARMTH_WEIGHT = 0.40
SEGMENT_WEIGHT = 0.25
URGENCY_WEIGHT = 0.35

# Urgency scores by resurrection hook type
URGENCY_SCORES = {
    "they_waiting": 100,
    "question_unanswered": 90,
    "promise_made": 70,
    "dormant": 40,
}

# Human-readable descriptions for hook types
HOOK_DESCRIPTIONS = {
    "they_waiting": "They're waiting for your reply",
    "question_unanswered": "They asked a question you haven't answered",
    "promise_made": "You made a promise you haven't fulfilled",
    "dormant": "Warm relationship gone quiet — good time to reconnect",
}

SEGMENT_DESCRIPTIONS = {
    "mujertech": "Part of MujerTech network",
    "cascadia": "In the Cascadia AI community",
    "job_target": "Works at a target company",
}


def calculate_segment_score(
    segment_tags: Optional[list[str]],
    manual_tags: Optional[list[str]],
) -> int:
    """
    Score based on segment membership.
    30 points per segment, +10 bonus for job_target.
    """
    if not segment_tags and not manual_tags:
        return 0

    all_tags = set(segment_tags or []) | set(manual_tags or [])
    score = min(len(all_tags) * 30, 90)

    if "job_target" in all_tags:
        score += 10

    return min(score, 100)


def calculate_urgency_score(opportunities: list[dict]) -> int:
    """
    Score based on the most urgent active resurrection opportunity.
    Returns the highest urgency score among all active hooks.
    """
    if not opportunities:
        return 0

    max_score = 0
    for opp in opportunities:
        hook_score = URGENCY_SCORES.get(opp["hook_type"], 0)
        max_score = max(max_score, hook_score)

    return max_score


def calculate_priority_score(
    warmth: int,
    segment_score: int,
    urgency_score: int,
) -> float:
    """Weighted composite priority score (0-100)."""
    return round(
        (warmth * WARMTH_WEIGHT)
        + (segment_score * SEGMENT_WEIGHT)
        + (urgency_score * URGENCY_WEIGHT),
        1,
    )


def build_reasons(
    warmth: int,
    segment_tags: Optional[list[str]],
    opportunities: list[dict],
) -> list[str]:
    """Build human-readable list of reasons to reach out."""
    reasons = []

    # Resurrection hooks first (most actionable)
    for opp in opportunities:
        desc = HOOK_DESCRIPTIONS.get(opp["hook_type"])
        if desc:
            reasons.append(desc)

    # Segment membership
    for tag in (segment_tags or []):
        desc = SEGMENT_DESCRIPTIONS.get(tag)
        if desc:
            reasons.append(desc)

    # Warmth tier
    if warmth >= 70:
        reasons.append("Strong relationship")
    elif warmth >= 40:
        reasons.append("Warm relationship")

    return reasons


async def get_daily_recommendations(
    db: AsyncSession,
    limit: int = 15,
    segment: Optional[str] = None,
) -> dict:
    """
    Get ranked outreach recommendations.

    Returns contacts sorted by priority score, excluding those
    already in the outreach queue (draft/approved).
    """
    # Subquery: contact IDs already in active queue
    queued_ids_stmt = (
        select(OutreachQueueItem.contact_id)
        .where(OutreachQueueItem.status.in_(["draft", "approved"]))
    )
    queued_result = await db.execute(queued_ids_stmt)
    queued_ids = {row[0] for row in queued_result.all()}

    # Get contacts with warmth > 0
    contact_stmt = select(Contact).where(Contact.warmth_score > 0)

    if segment:
        from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
        contact_stmt = contact_stmt.where(Contact.segment_tags.contains([segment]))

    contact_result = await db.execute(contact_stmt)
    contacts = contact_result.scalars().all()

    # Get all active resurrection opportunities, grouped by contact_id
    opp_stmt = select(ResurrectionOpportunity).where(
        ResurrectionOpportunity.is_active == True
    )
    opp_result = await db.execute(opp_stmt)
    all_opps = opp_result.scalars().all()

    opps_by_contact: dict[UUID, list[dict]] = {}
    for opp in all_opps:
        contact_opps = opps_by_contact.setdefault(opp.contact_id, [])
        contact_opps.append({
            "hook_type": opp.hook_type,
            "hook_detail": opp.hook_detail,
        })

    # Score and rank each contact
    recommendations = []
    total_eligible = 0

    for contact in contacts:
        # Skip contacts already in queue
        if contact.id in queued_ids:
            continue

        total_eligible += 1

        warmth = contact.warmth_score or 0
        contact_opps = opps_by_contact.get(contact.id, [])

        segment_score = calculate_segment_score(contact.segment_tags, contact.manual_tags)
        urgency_score = calculate_urgency_score(contact_opps)
        priority = calculate_priority_score(warmth, segment_score, urgency_score)
        reasons = build_reasons(warmth, contact.segment_tags, contact_opps)

        recommendations.append({
            "contact_id": str(contact.id),
            "contact_name": contact.name,
            "contact_company": contact.company,
            "contact_headline": contact.headline,
            "contact_linkedin_url": contact.linkedin_url,
            "warmth_score": warmth,
            "segment_tags": contact.segment_tags,
            "priority_score": priority,
            "priority_breakdown": {
                "warmth_component": round(warmth * WARMTH_WEIGHT, 1),
                "segment_component": round(segment_score * SEGMENT_WEIGHT, 1),
                "urgency_component": round(urgency_score * URGENCY_WEIGHT, 1),
            },
            "reasons": reasons,
            "resurrection_hooks": contact_opps,
        })

    # Sort by priority score descending
    recommendations.sort(key=lambda r: r["priority_score"], reverse=True)

    return {
        "recommendations": recommendations[:limit],
        "total_eligible": total_eligible,
        "generated_at": datetime.utcnow().isoformat(),
    }


async def get_contact_priority(
    db: AsyncSession,
    contact_id: UUID,
) -> Optional[dict]:
    """Get priority breakdown for a single contact."""
    # Get contact
    contact_stmt = select(Contact).where(Contact.id == contact_id)
    contact_result = await db.execute(contact_stmt)
    contact = contact_result.scalar_one_or_none()

    if not contact:
        return None

    # Get active resurrection opportunities
    opp_stmt = select(ResurrectionOpportunity).where(
        ResurrectionOpportunity.contact_id == contact_id,
        ResurrectionOpportunity.is_active == True,
    )
    opp_result = await db.execute(opp_stmt)
    contact_opps = [
        {"hook_type": opp.hook_type, "hook_detail": opp.hook_detail}
        for opp in opp_result.scalars().all()
    ]

    # Check if in queue
    queue_stmt = select(OutreachQueueItem).where(
        OutreachQueueItem.contact_id == contact_id,
        OutreachQueueItem.status.in_(["draft", "approved"]),
    )
    queue_result = await db.execute(queue_stmt)
    in_queue = queue_result.scalar_one_or_none() is not None

    warmth = contact.warmth_score or 0
    segment_score = calculate_segment_score(contact.segment_tags, contact.manual_tags)
    urgency_score = calculate_urgency_score(contact_opps)
    priority = calculate_priority_score(warmth, segment_score, urgency_score)
    reasons = build_reasons(warmth, contact.segment_tags, contact_opps)

    return {
        "contact_id": str(contact.id),
        "contact_name": contact.name,
        "priority_score": priority,
        "priority_breakdown": {
            "warmth_component": round(warmth * WARMTH_WEIGHT, 1),
            "segment_component": round(segment_score * SEGMENT_WEIGHT, 1),
            "urgency_component": round(urgency_score * URGENCY_WEIGHT, 1),
        },
        "reasons": reasons,
        "resurrection_hooks": contact_opps,
        "in_queue": in_queue,
    }
