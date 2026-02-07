"""
Resurrection Scanner Service

Detects outreach opportunities by analyzing message patterns:
- Dormant relationships (warm contacts gone quiet)
- Broken promises (you said "I'll..." but didn't follow up)
- Unanswered questions (they asked, you didn't respond)
- They're waiting (ball is in your court)
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, Message, ResurrectionOpportunity


# ============================================================================
# Configuration
# ============================================================================

DORMANT_DAYS = 60  # Days without contact to consider dormant
DORMANT_MIN_WARMTH = 40  # Minimum warmth score to flag as dormant
PROMISE_LOOKBACK_DAYS = 90  # How far back to look for unfulfilled promises
QUESTION_LOOKBACK_DAYS = 30  # How far back to look for unanswered questions

# Patterns that suggest a promise or commitment
PROMISE_PATTERNS = [
    r"\bi'?ll\b",  # I'll, Ill
    r"\bi will\b",
    r"\blet me\b",
    r"\bi'?m going to\b",
    r"\bwill send\b",
    r"\bwill share\b",
    r"\bwill get back\b",
    r"\bwill follow up\b",
    r"\bwill reach out\b",
    r"\bwill connect you\b",
    r"\bwill introduce\b",
    r"\bwill check\b",
    r"\bwill look into\b",
]

# Compile patterns for efficiency
PROMISE_REGEX = re.compile("|".join(PROMISE_PATTERNS), re.IGNORECASE)


def extract_promise_context(content: str) -> Optional[str]:
    """Extract the sentence containing the promise for context."""
    if not content:
        return None

    match = PROMISE_REGEX.search(content)
    if not match:
        return None

    # Find the sentence containing the match
    start = content.rfind(".", 0, match.start())
    start = start + 1 if start != -1 else 0

    end = content.find(".", match.end())
    end = end + 1 if end != -1 else len(content)

    sentence = content[start:end].strip()

    # Limit length
    if len(sentence) > 200:
        sentence = sentence[:200] + "..."

    return sentence


def extract_question_context(content: str) -> Optional[str]:
    """Extract the question from the message."""
    if not content:
        return None

    # Find sentences ending with ?
    sentences = re.split(r'(?<=[.!?])\s+', content)
    questions = [s.strip() for s in sentences if s.strip().endswith("?")]

    if not questions:
        return None

    # Return the last question (most likely the one needing response)
    question = questions[-1]

    # Limit length
    if len(question) > 200:
        question = question[:200] + "..."

    return question


def has_question(content: str) -> bool:
    """Check if message contains a substantive question."""
    if not content or "?" not in content:
        return False

    # Filter out rhetorical/shallow questions
    shallow_patterns = [
        r"how are you\?",
        r"how's it going\?",
        r"what's up\?",
        r"how have you been\?",
        r"right\?",
        r"you know\?",
        r"isn't it\?",
        r"don't you think\?",
    ]

    content_lower = content.lower()

    # If only contains shallow questions, not substantive
    questions = re.findall(r'[^.!?]*\?', content)
    for q in questions:
        q_lower = q.lower()
        is_shallow = any(re.search(p, q_lower) for p in shallow_patterns)
        if not is_shallow and len(q) > 10:
            return True

    return False


# ============================================================================
# Dormant Relationships Scanner
# ============================================================================

async def scan_dormant_relationships(db: AsyncSession) -> dict:
    """
    Find warm contacts you haven't communicated with recently.

    Criteria:
    - Warmth score >= DORMANT_MIN_WARMTH
    - Last message > DORMANT_DAYS ago
    """
    result = {"found": 0, "created": 0, "updated": 0}

    cutoff_date = datetime.utcnow() - timedelta(days=DORMANT_DAYS)

    # Find warm contacts with old last message
    stmt = select(Contact).where(
        and_(
            Contact.warmth_score >= DORMANT_MIN_WARMTH,
            Contact.last_message_date < cutoff_date.date(),
        )
    )

    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        result["found"] += 1

        days_since = (datetime.utcnow().date() - contact.last_message_date).days
        hook_detail = f"Last message was {days_since} days ago. Warmth score: {contact.warmth_score}"

        # Check if opportunity already exists
        existing_stmt = select(ResurrectionOpportunity).where(
            and_(
                ResurrectionOpportunity.contact_id == contact.id,
                ResurrectionOpportunity.hook_type == "dormant",
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.hook_detail = hook_detail
            existing.detected_at = datetime.utcnow()
            existing.is_active = True
            result["updated"] += 1
        else:
            opportunity = ResurrectionOpportunity(
                contact_id=contact.id,
                hook_type="dormant",
                hook_detail=hook_detail,
            )
            db.add(opportunity)
            result["created"] += 1

    return result


# ============================================================================
# Broken Promises Scanner
# ============================================================================

async def scan_broken_promises(db: AsyncSession) -> dict:
    """
    Find messages where you made a promise but didn't follow up.

    Criteria:
    - Message you sent contains promise patterns
    - No subsequent message from you to that contact
    - Message is within lookback period
    """
    result = {"found": 0, "created": 0, "updated": 0}

    cutoff_date = datetime.utcnow() - timedelta(days=PROMISE_LOOKBACK_DAYS)

    # Get all sent messages in lookback period
    stmt = select(Message).where(
        and_(
            Message.direction == "sent",
            Message.date >= cutoff_date,
            Message.content.isnot(None),
        )
    ).order_by(Message.contact_id, Message.date)

    messages_result = await db.execute(stmt)
    messages = messages_result.scalars().all()

    # Group by contact
    contact_messages: dict = {}
    for msg in messages:
        if msg.contact_id not in contact_messages:
            contact_messages[msg.contact_id] = []
        contact_messages[msg.contact_id].append(msg)

    for contact_id, msgs in contact_messages.items():
        # Check each message for promises
        for i, msg in enumerate(msgs):
            if not msg.content:
                continue

            promise_context = extract_promise_context(msg.content)
            if not promise_context:
                continue

            # Check if there was a follow-up message after this one
            later_messages = [m for m in msgs if m.date > msg.date]

            if later_messages:
                # There was follow-up, skip
                continue

            # This is a potentially broken promise
            result["found"] += 1

            days_since = (datetime.utcnow() - msg.date).days
            hook_detail = f'You said: "{promise_context}" ({days_since} days ago)'

            # Check if opportunity already exists
            existing_stmt = select(ResurrectionOpportunity).where(
                and_(
                    ResurrectionOpportunity.contact_id == contact_id,
                    ResurrectionOpportunity.hook_type == "promise_made",
                )
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.hook_detail = hook_detail
                existing.source_message_id = msg.id
                existing.detected_at = datetime.utcnow()
                existing.is_active = True
                result["updated"] += 1
            else:
                opportunity = ResurrectionOpportunity(
                    contact_id=contact_id,
                    hook_type="promise_made",
                    hook_detail=hook_detail,
                    source_message_id=msg.id,
                )
                db.add(opportunity)
                result["created"] += 1

            # Only flag one promise per contact (the most recent)
            break

    return result


# ============================================================================
# Unanswered Questions Scanner
# ============================================================================

async def scan_unanswered_questions(db: AsyncSession) -> dict:
    """
    Find messages where they asked you a question you never answered.

    Criteria:
    - Message received contains a question
    - No subsequent message from you to that contact
    - Message is within lookback period
    """
    result = {"found": 0, "created": 0, "updated": 0}

    cutoff_date = datetime.utcnow() - timedelta(days=QUESTION_LOOKBACK_DAYS)

    # Get contacts where last message was received (not sent)
    stmt = select(Contact).where(
        Contact.last_message_direction == "received"
    )

    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        # Get their last message
        msg_stmt = select(Message).where(
            and_(
                Message.contact_id == contact.id,
                Message.direction == "received",
                Message.date >= cutoff_date,
            )
        ).order_by(desc(Message.date)).limit(1)

        msg_result = await db.execute(msg_stmt)
        last_received = msg_result.scalar_one_or_none()

        if not last_received or not last_received.content:
            continue

        if not has_question(last_received.content):
            continue

        question_context = extract_question_context(last_received.content)
        if not question_context:
            continue

        result["found"] += 1

        days_since = (datetime.utcnow() - last_received.date).days
        hook_detail = f'They asked: "{question_context}" ({days_since} days ago)'

        # Check if opportunity already exists
        existing_stmt = select(ResurrectionOpportunity).where(
            and_(
                ResurrectionOpportunity.contact_id == contact.id,
                ResurrectionOpportunity.hook_type == "question_unanswered",
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.hook_detail = hook_detail
            existing.source_message_id = last_received.id
            existing.detected_at = datetime.utcnow()
            existing.is_active = True
            result["updated"] += 1
        else:
            opportunity = ResurrectionOpportunity(
                contact_id=contact.id,
                hook_type="question_unanswered",
                hook_detail=hook_detail,
                source_message_id=last_received.id,
            )
            db.add(opportunity)
            result["created"] += 1

    return result


# ============================================================================
# They're Waiting Scanner
# ============================================================================

async def scan_they_waiting(db: AsyncSession) -> dict:
    """
    Find contacts where the ball is in your court.

    Criteria:
    - Last message direction was 'received' (they messaged you)
    - Not already flagged as unanswered question
    - Has some warmth (engaged contact)
    """
    result = {"found": 0, "created": 0, "updated": 0}

    cutoff_date = datetime.utcnow() - timedelta(days=QUESTION_LOOKBACK_DAYS)

    # Find contacts where last message was received and has warmth
    stmt = select(Contact).where(
        and_(
            Contact.last_message_direction == "received",
            Contact.warmth_score >= 10,  # Some engagement
            Contact.last_message_date >= cutoff_date.date(),
        )
    )

    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        # Skip if already has unanswered question (more specific hook)
        existing_question_stmt = select(ResurrectionOpportunity).where(
            and_(
                ResurrectionOpportunity.contact_id == contact.id,
                ResurrectionOpportunity.hook_type == "question_unanswered",
                ResurrectionOpportunity.is_active == True,
            )
        )
        existing_q_result = await db.execute(existing_question_stmt)
        if existing_q_result.scalar_one_or_none():
            continue

        result["found"] += 1

        days_since = (datetime.utcnow().date() - contact.last_message_date).days
        hook_detail = f"Their last message was {days_since} days ago. Ball is in your court."

        # Check if opportunity already exists
        existing_stmt = select(ResurrectionOpportunity).where(
            and_(
                ResurrectionOpportunity.contact_id == contact.id,
                ResurrectionOpportunity.hook_type == "they_waiting",
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.hook_detail = hook_detail
            existing.detected_at = datetime.utcnow()
            existing.is_active = True
            result["updated"] += 1
        else:
            opportunity = ResurrectionOpportunity(
                contact_id=contact.id,
                hook_type="they_waiting",
                hook_detail=hook_detail,
            )
            db.add(opportunity)
            result["created"] += 1

    return result


# ============================================================================
# Main Scanner Function
# ============================================================================

async def run_full_scan(db: AsyncSession) -> dict:
    """
    Run all resurrection scanners.

    Returns combined stats.
    """
    results = {
        "dormant": await scan_dormant_relationships(db),
        "promises": await scan_broken_promises(db),
        "questions": await scan_unanswered_questions(db),
        "waiting": await scan_they_waiting(db),
    }

    await db.commit()

    # Calculate totals
    total_found = sum(r["found"] for r in results.values())
    total_created = sum(r["created"] for r in results.values())
    total_updated = sum(r["updated"] for r in results.values())

    return {
        "total_opportunities_found": total_found,
        "new_opportunities": total_created,
        "updated_opportunities": total_updated,
        "by_type": results,
    }


async def get_active_opportunities(
    db: AsyncSession,
    hook_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    Get active resurrection opportunities with contact info.

    Returns list of opportunities sorted by contact warmth.
    """
    stmt = select(ResurrectionOpportunity, Contact).join(
        Contact, ResurrectionOpportunity.contact_id == Contact.id
    ).where(
        ResurrectionOpportunity.is_active == True
    )

    if hook_type:
        stmt = stmt.where(ResurrectionOpportunity.hook_type == hook_type)

    stmt = stmt.order_by(desc(Contact.warmth_score)).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    opportunities = []
    for opp, contact in rows:
        opportunities.append({
            "id": str(opp.id),
            "contact_id": str(contact.id),
            "contact_name": contact.name,
            "contact_company": contact.company,
            "contact_headline": contact.headline,
            "contact_linkedin_url": contact.linkedin_url,
            "warmth_score": contact.warmth_score,
            "hook_type": opp.hook_type,
            "hook_detail": opp.hook_detail,
            "detected_at": opp.detected_at.isoformat(),
        })

    return opportunities


async def dismiss_opportunity(db: AsyncSession, opportunity_id: str) -> bool:
    """Mark an opportunity as addressed/dismissed."""
    from uuid import UUID

    stmt = select(ResurrectionOpportunity).where(
        ResurrectionOpportunity.id == UUID(opportunity_id)
    )
    result = await db.execute(stmt)
    opp = result.scalar_one_or_none()

    if not opp:
        return False

    opp.is_active = False
    await db.commit()
    return True
