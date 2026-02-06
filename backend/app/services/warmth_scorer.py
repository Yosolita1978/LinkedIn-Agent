"""
Warmth Scoring Engine

Calculates relationship strength for each contact based on message history.
Total score: 0-100 points across 5 components.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, Message


# Shallow message patterns - these don't count as substantive
SHALLOW_PATTERNS = [
    r"^thanks?!*$",
    r"^thank you!*$",
    r"^congrats!*$",
    r"^congratulations!*$",
    r"^happy birthday!*$",
    r"^welcome!*$",
    r"^great!*$",
    r"^awesome!*$",
    r"^nice!*$",
    r"^cool!*$",
    r"^ok!*$",
    r"^okay!*$",
    r"^sure!*$",
    r"^yes!*$",
    r"^no!*$",
    r"^👍+$",
    r"^🎉+$",
    r"^😊+$",
    r"^🙏+$",
    r"^❤️+$",
]

# Minimum length for a substantive message
MIN_SUBSTANTIVE_LENGTH = 100


def is_message_substantive(content: Optional[str]) -> bool:
    """
    Determine if a message is substantive (meaningful content).

    A message is substantive if:
    - Length > 100 characters AND
    - Does NOT match shallow patterns
    """
    if not content:
        return False

    content_stripped = content.strip().lower()

    # Check length
    if len(content_stripped) < MIN_SUBSTANTIVE_LENGTH:
        return False

    # Check against shallow patterns
    for pattern in SHALLOW_PATTERNS:
        if re.match(pattern, content_stripped, re.IGNORECASE):
            return False

    return True


def calculate_recency_score(days_since_last_message: Optional[int]) -> int:
    """
    Calculate recency score (0-30 points).

    - 30 points if < 7 days
    - Linear decay to 0 at 365+ days
    """
    if days_since_last_message is None:
        return 0

    if days_since_last_message < 7:
        return 30
    elif days_since_last_message >= 365:
        return 0
    else:
        # Linear decay from 30 to 0 over 358 days (7 to 365)
        score = 30 - int((days_since_last_message - 7) * 30 / 358)
        return max(0, score)


def calculate_frequency_score(total_messages: int) -> int:
    """
    Calculate frequency score (0-20 points).

    - 20 points at 50+ messages
    - Scales linearly below that
    """
    if total_messages >= 50:
        return 20
    return int(total_messages * 20 / 50)


def calculate_depth_score(
    avg_message_length: float,
    substantive_ratio: float,
) -> int:
    """
    Calculate depth score (0-25 points).

    Based on:
    - Average message length (0-15 points)
    - Ratio of substantive messages (0-10 points)
    """
    # Length component (0-15 points)
    # 15 points at 500+ chars average, scales linearly
    if avg_message_length >= 500:
        length_score = 15
    else:
        length_score = int(avg_message_length * 15 / 500)

    # Substantive ratio component (0-10 points)
    # 10 points at 50%+ substantive, scales linearly
    if substantive_ratio >= 0.5:
        substantive_score = 10
    else:
        substantive_score = int(substantive_ratio * 10 / 0.5)

    return length_score + substantive_score


def calculate_responsiveness_score(
    messages_received: int,
    messages_sent: int,
) -> int:
    """
    Calculate responsiveness score (0-15 points).

    Based on response rate - do they reply to your messages?
    If you sent 10 messages and received 8, that's 80% response rate.
    """
    if messages_sent == 0:
        return 0

    # Response rate: received / sent (capped at 1.0)
    response_rate = min(messages_received / messages_sent, 1.0)

    return int(response_rate * 15)


def calculate_initiation_score(
    messages_sent: int,
    messages_received: int,
) -> int:
    """
    Calculate initiation balance score (0-10 points).

    Balanced conversations (both parties initiate) score higher.
    One-sided conversations (you always initiate OR they always initiate) score lower.

    Perfect balance (50/50) = 10 points
    Complete imbalance (100/0) = 0 points
    """
    total = messages_sent + messages_received
    if total == 0:
        return 0

    # Calculate how balanced the conversation is
    sent_ratio = messages_sent / total

    # Balance score: 1.0 at 50/50, 0 at 100/0 or 0/100
    # Using: 1 - |sent_ratio - 0.5| * 2
    balance = 1 - abs(sent_ratio - 0.5) * 2

    return int(balance * 10)


async def calculate_contact_warmth(
    db: AsyncSession,
    contact: Contact,
) -> dict:
    """
    Calculate warmth score and breakdown for a single contact.

    Returns dict with score and breakdown.
    """
    # Get all messages for this contact
    stmt = select(Message).where(Message.contact_id == contact.id)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        return {
            "warmth_score": 0,
            "warmth_breakdown": {
                "recency": 0,
                "frequency": 0,
                "depth": 0,
                "responsiveness": 0,
                "initiation": 0,
            },
        }

    # Calculate metrics
    now = datetime.utcnow()

    # Sort by date to find most recent
    messages_sorted = sorted(messages, key=lambda m: m.date, reverse=True)
    last_message_date = messages_sorted[0].date
    days_since_last = (now - last_message_date).days

    # Count by direction
    messages_sent = sum(1 for m in messages if m.direction == "sent")
    messages_received = sum(1 for m in messages if m.direction == "received")
    total_messages = len(messages)

    # Calculate average message length (only for messages with content)
    messages_with_content = [m for m in messages if m.content]
    if messages_with_content:
        avg_length = sum(len(m.content) for m in messages_with_content) / len(messages_with_content)
    else:
        avg_length = 0

    # Calculate substantive ratio
    substantive_count = sum(1 for m in messages if is_message_substantive(m.content))
    substantive_ratio = substantive_count / total_messages if total_messages > 0 else 0

    # Calculate component scores
    recency = calculate_recency_score(days_since_last)
    frequency = calculate_frequency_score(total_messages)
    depth = calculate_depth_score(avg_length, substantive_ratio)
    responsiveness = calculate_responsiveness_score(messages_received, messages_sent)
    initiation = calculate_initiation_score(messages_sent, messages_received)

    warmth_score = recency + frequency + depth + responsiveness + initiation

    return {
        "warmth_score": warmth_score,
        "warmth_breakdown": {
            "recency": recency,
            "frequency": frequency,
            "depth": depth,
            "responsiveness": responsiveness,
            "initiation": initiation,
        },
    }


async def update_contact_warmth(db: AsyncSession, contact: Contact) -> None:
    """Update warmth score for a single contact."""
    result = await calculate_contact_warmth(db, contact)

    contact.warmth_score = result["warmth_score"]
    contact.warmth_breakdown = result["warmth_breakdown"]
    contact.warmth_calculated_at = datetime.utcnow()


async def update_message_substantive_flags(db: AsyncSession) -> int:
    """
    Update is_substantive flag for all messages.

    Returns count of messages updated.
    """
    stmt = select(Message).where(Message.is_substantive.is_(None))
    result = await db.execute(stmt)
    messages = result.scalars().all()

    count = 0
    for message in messages:
        message.is_substantive = is_message_substantive(message.content)
        count += 1

    await db.commit()
    return count


async def recalculate_all_warmth_scores(db: AsyncSession) -> dict:
    """
    Recalculate warmth scores for all contacts with messages.

    Returns dict with processing stats.
    """
    result = {
        "contacts_processed": 0,
        "contacts_with_messages": 0,
        "contacts_without_messages": 0,
    }

    # Get all contacts
    stmt = select(Contact)
    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        await update_contact_warmth(db, contact)
        result["contacts_processed"] += 1

        if contact.warmth_score and contact.warmth_score > 0:
            result["contacts_with_messages"] += 1
        else:
            result["contacts_without_messages"] += 1

    await db.commit()

    return result


async def recalculate_warmth_for_contacts_with_messages(db: AsyncSession) -> dict:
    """
    Recalculate warmth scores only for contacts that have messages.
    More efficient than recalculating all.

    Returns dict with processing stats.
    """
    result = {
        "contacts_processed": 0,
    }

    # Get contacts that have at least one message
    stmt = (
        select(Contact)
        .where(Contact.total_messages > 0)
    )
    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        await update_contact_warmth(db, contact)
        result["contacts_processed"] += 1

    await db.commit()

    return result
