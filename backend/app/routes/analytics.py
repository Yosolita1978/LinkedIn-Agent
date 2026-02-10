"""
Analytics routes — network intelligence and insights.

Module 1: Network Overview (GET /api/analytics/overview)
  - Total contacts, unique companies, segment distribution
  - Warmth distribution and averages by segment
  - Top companies by contact count
  - Network archetype classification
  - Senior contact percentage
"""

import re
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Contact


router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Title patterns that indicate senior-level contacts
SENIOR_PATTERNS = re.compile(
    r"\b("
    r"vp|vice president|"
    r"director|"
    r"c[etofi]o|chief|"
    r"head of|"
    r"president|"
    r"partner|"
    r"founder|co-founder|cofounder|"
    r"general manager|"
    r"svp|evp|"
    r"principal|"
    r"fellow"
    r")\b",
    re.IGNORECASE,
)


def classify_archetype(
    unique_companies: int,
    total_contacts: int,
    senior_pct: float,
    avg_contacts_per_company: float,
    top_company_concentration: float,
) -> dict:
    """
    Classify network into one of 5 archetypes based on connection patterns.

    - Thought Leader: Wide reach, many unique companies, low concentration
    - Insider: Dense connections at few companies, high concentration
    - Connector: High company diversity, moderate contact count
    - Climber: High senior-title density (VP, C-suite, Director)
    - Builder: Moderate network, balanced characteristics

    Returns dict with archetype name, description, and strategy.
    """
    scores = {
        "Thought Leader": 0,
        "Insider": 0,
        "Connector": 0,
        "Climber": 0,
        "Builder": 0,
    }

    # High company diversity → Thought Leader or Connector
    if total_contacts > 0:
        diversity_ratio = unique_companies / total_contacts
        if diversity_ratio > 0.6:
            scores["Connector"] += 3
            scores["Thought Leader"] += 2
        elif diversity_ratio > 0.4:
            scores["Connector"] += 2
            scores["Thought Leader"] += 1

    # High concentration at few companies → Insider
    if top_company_concentration > 0.15:
        scores["Insider"] += 3
    elif top_company_concentration > 0.08:
        scores["Insider"] += 1

    # High avg contacts per company → Insider
    if avg_contacts_per_company > 3:
        scores["Insider"] += 2

    # High senior % → Climber
    if senior_pct > 35:
        scores["Climber"] += 3
    elif senior_pct > 25:
        scores["Climber"] += 2

    # Large network → Thought Leader
    if total_contacts > 2000:
        scores["Thought Leader"] += 2
    elif total_contacts > 1000:
        scores["Thought Leader"] += 1

    # Moderate everything → Builder
    if (
        diversity_ratio > 0.3
        and senior_pct > 10
        and total_contacts > 200
        and top_company_concentration < 0.15
    ):
        scores["Builder"] += 2

    archetype = max(scores, key=scores.get)

    descriptions = {
        "Thought Leader": {
            "description": "Wide reach across many organizations. Your network spans industries and roles.",
            "strategy": "Leverage broadcasting — a single post about your goals could generate dozens of warm leads.",
        },
        "Insider": {
            "description": "Deep connections within a few key companies. Strong institutional knowledge.",
            "strategy": "Work your internal networks. You have density where it matters — use referrals and insider knowledge.",
        },
        "Connector": {
            "description": "High diversity across many unique companies with strong bridging potential.",
            "strategy": "Trade introductions. Your value is in connecting people across different circles.",
        },
        "Climber": {
            "description": "High access to senior leaders — VPs, Directors, C-suite, and Founders.",
            "strategy": "Target executive referrals. You have decision-maker access most people don't.",
        },
        "Builder": {
            "description": "Balanced, growing network with a mix of seniority and company diversity.",
            "strategy": "Invest in depth. Turn surface connections into substantive relationships through consistent engagement.",
        },
    }

    return {
        "archetype": archetype,
        "scores": scores,
        **descriptions[archetype],
    }


@router.get("/overview")
async def get_network_overview(db: AsyncSession = Depends(get_db)):
    """
    Network Overview — Module 1.

    Returns a comprehensive snapshot of your network:
    - Contact totals and warmth distribution
    - Segment distribution with average warmth per segment
    - Top 10 companies by contact count
    - Network archetype classification
    - Senior contact percentage
    """
    # --- Basic counts ---
    total_result = await db.execute(select(func.count(Contact.id)))
    total_contacts = total_result.scalar() or 0

    with_messages_result = await db.execute(
        select(func.count(Contact.id)).where(Contact.total_messages > 0)
    )
    contacts_with_messages = with_messages_result.scalar() or 0

    # --- Unique companies ---
    unique_companies_result = await db.execute(
        select(func.count(func.distinct(Contact.company))).where(
            Contact.company.isnot(None),
            Contact.company != "",
        )
    )
    unique_companies = unique_companies_result.scalar() or 0

    # --- Warmth distribution ---
    warmth_buckets = {}
    bucket_queries = [
        ("hot", Contact.warmth_score >= 70),
        ("warm", and_(Contact.warmth_score >= 40, Contact.warmth_score < 70)),
        ("cool", and_(Contact.warmth_score >= 10, Contact.warmth_score < 40)),
        ("cold", and_(Contact.warmth_score >= 1, Contact.warmth_score < 10)),
    ]
    for bucket_name, condition in bucket_queries:
        result = await db.execute(
            select(func.count(Contact.id)).where(condition)
        )
        warmth_buckets[bucket_name] = result.scalar() or 0

    warmth_buckets["none"] = total_contacts - sum(warmth_buckets.values())

    avg_warmth_result = await db.execute(
        select(func.avg(Contact.warmth_score)).where(Contact.warmth_score > 0)
    )
    avg_warmth = avg_warmth_result.scalar()

    # --- Segment distribution with average warmth ---
    segments = {}
    for tag in ["mujertech", "cascadia", "job_target"]:
        seg_filter = Contact.segment_tags.contains([tag])

        count_result = await db.execute(
            select(func.count(Contact.id)).where(seg_filter)
        )
        seg_count = count_result.scalar() or 0

        avg_result = await db.execute(
            select(func.avg(Contact.warmth_score)).where(
                seg_filter, Contact.warmth_score > 0
            )
        )
        seg_avg = avg_result.scalar()

        segments[tag] = {
            "count": seg_count,
            "average_warmth": round(seg_avg, 1) if seg_avg else 0,
        }

    # Untagged contacts
    untagged_result = await db.execute(
        select(func.count(Contact.id)).where(
            (Contact.segment_tags.is_(None)) | (Contact.segment_tags == [])
        )
    )
    untagged_count = untagged_result.scalar() or 0

    untagged_avg_result = await db.execute(
        select(func.avg(Contact.warmth_score)).where(
            (Contact.segment_tags.is_(None)) | (Contact.segment_tags == []),
            Contact.warmth_score > 0,
        )
    )
    untagged_avg = untagged_avg_result.scalar()

    segments["untagged"] = {
        "count": untagged_count,
        "average_warmth": round(untagged_avg, 1) if untagged_avg else 0,
    }

    # --- Top 10 companies by contact count ---
    top_companies_result = await db.execute(
        select(Contact.company, func.count(Contact.id).label("count"))
        .where(Contact.company.isnot(None), Contact.company != "")
        .group_by(Contact.company)
        .order_by(func.count(Contact.id).desc())
        .limit(10)
    )
    top_companies = [
        {"company": row.company, "count": row.count}
        for row in top_companies_result.all()
    ]

    # --- Senior contacts ---
    # Fetch all contacts with a position to check against regex
    position_result = await db.execute(
        select(Contact.position).where(
            Contact.position.isnot(None), Contact.position != ""
        )
    )
    positions = position_result.scalars().all()
    senior_count = sum(1 for p in positions if SENIOR_PATTERNS.search(p))
    senior_pct = round((senior_count / total_contacts) * 100, 1) if total_contacts > 0 else 0

    # --- Network archetype ---
    top_company_contacts = top_companies[0]["count"] if top_companies else 0
    top_company_concentration = (
        top_company_contacts / total_contacts if total_contacts > 0 else 0
    )
    avg_contacts_per_company = (
        total_contacts / unique_companies if unique_companies > 0 else 0
    )

    archetype = classify_archetype(
        unique_companies=unique_companies,
        total_contacts=total_contacts,
        senior_pct=senior_pct,
        avg_contacts_per_company=avg_contacts_per_company,
        top_company_concentration=top_company_concentration,
    )

    return {
        "totals": {
            "contacts": total_contacts,
            "with_messages": contacts_with_messages,
            "without_messages": total_contacts - contacts_with_messages,
            "unique_companies": unique_companies,
            "senior_contacts": senior_count,
            "senior_pct": senior_pct,
        },
        "warmth_distribution": warmth_buckets,
        "average_warmth": round(avg_warmth, 1) if avg_warmth else 0,
        "segments": segments,
        "top_companies": top_companies,
        "archetype": archetype,
    }
