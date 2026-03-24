"""
Inbox Service

Syncs LinkedIn conversations via Playwright browser automation and provides
inbox queries (conversations, needs-reply detection).
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, Message
from app.services.linkedin_browser import LinkedInBrowser

logger = logging.getLogger(__name__)


async def sync_conversations(
    db: AsyncSession,
    limit: int = 40,
) -> dict:
    """
    Scrape recent conversations from LinkedIn messaging via Playwright.

    For each conversation:
    1. Match participant name to an existing contact
    2. Store the last message preview as a synced message

    Returns a summary of what was synced.
    """
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            raise ValueError("LinkedIn session expired. Re-authenticate with test_auth.py.")

        conversations = await browser.scrape_inbox_conversations(max_items=limit)
        logger.info(f"Scraped {len(conversations)} conversations from LinkedIn")

        synced_conversations = 0
        new_messages = 0
        skipped_no_contact = 0

        now = datetime.utcnow()

        for conv in conversations:
            # Match participant name to existing contact
            contact = await _match_contact_by_name(db, conv["participant_name"])
            if not contact:
                skipped_no_contact += 1
                continue

            # Use the preview as the latest message
            preview = conv.get("last_message_preview", "")
            if not preview:
                synced_conversations += 1
                continue

            # Check if we already have this exact message (dedup by content + contact + date)
            # Use a simple check: same contact, same content prefix
            existing = await db.execute(
                select(Message)
                .where(Message.contact_id == contact.id)
                .where(Message.content == preview)
                .where(Message.synced_at.isnot(None))
            )
            if existing.scalar_one_or_none():
                synced_conversations += 1
                continue

            # Determine direction from preview text
            # LinkedIn prefixes your messages with "You: "
            direction = "sent" if preview.startswith("You: ") else "received"
            content = preview.removeprefix("You: ")

            content_length = len(content) if content else 0
            is_substantive = _is_substantive(content)

            new_msg = Message(
                contact_id=contact.id,
                direction=direction,
                date=now,
                content=content,
                content_length=content_length,
                is_substantive=is_substantive,
                conversation_id=conv.get("conversation_link", ""),
                synced_at=now,
            )
            db.add(new_msg)
            new_messages += 1
            synced_conversations += 1

        # Update needs_reply and contact stats
        await db.flush()
        await _update_needs_reply(db)
        await _update_contact_message_stats(db)
        await db.commit()

    return {
        "conversations_fetched": len(conversations),
        "conversations_synced": synced_conversations,
        "new_messages": new_messages,
        "skipped_no_contact": skipped_no_contact,
    }


async def get_inbox(
    db: AsyncSession,
    filter_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    Get inbox conversations grouped by contact.

    filter_type: "needs_reply", "waiting", or None for all
    """
    # Subquery: latest message per contact
    latest_msg_subq = (
        select(
            Message.contact_id,
            func.max(Message.date).label("last_date"),
        )
        .where(Message.conversation_id.isnot(None))
        .group_by(Message.contact_id)
        .subquery()
    )

    # Main query: contacts with conversations
    stmt = (
        select(
            Contact.id,
            Contact.name,
            Contact.company,
            Contact.headline,
            Contact.linkedin_url,
            Contact.warmth_score,
            latest_msg_subq.c.last_date,
        )
        .join(latest_msg_subq, Contact.id == latest_msg_subq.c.contact_id)
        .order_by(desc(latest_msg_subq.c.last_date))
    )

    # Apply filters
    if filter_type == "needs_reply":
        # Last message from them (direction = received) and no reply after it
        needs_reply_contacts = await _get_needs_reply_contact_ids(db)
        if needs_reply_contacts:
            stmt = stmt.where(Contact.id.in_(needs_reply_contacts))
        else:
            return [], 0
    elif filter_type == "waiting":
        # Last message from us (direction = sent) — waiting for their reply
        waiting_contacts = await _get_waiting_contact_ids(db)
        if waiting_contacts:
            stmt = stmt.where(Contact.id.in_(waiting_contacts))
        else:
            return [], 0

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    conversations = []
    for row in rows:
        contact_id = row[0]

        # Get last message for preview
        last_msg_stmt = (
            select(Message)
            .where(Message.contact_id == contact_id)
            .order_by(desc(Message.date))
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_stmt)
        last_msg = last_msg_result.scalar_one_or_none()

        # Count unsynced/total messages
        msg_count_stmt = (
            select(func.count(Message.id))
            .where(Message.contact_id == contact_id)
        )
        msg_count_result = await db.execute(msg_count_stmt)
        msg_count = msg_count_result.scalar() or 0

        # Check if needs reply
        needs_reply = last_msg.direction == "received" if last_msg else False

        conversations.append({
            "contact_id": str(contact_id),
            "contact_name": row[1],
            "contact_company": row[2],
            "contact_headline": row[3],
            "contact_linkedin_url": row[4],
            "warmth_score": row[5],
            "last_message_date": row[6].isoformat() if row[6] else None,
            "last_message_preview": (last_msg.content[:100] + "..." if last_msg and last_msg.content and len(last_msg.content) > 100 else last_msg.content) if last_msg else None,
            "last_message_direction": last_msg.direction if last_msg else None,
            "total_messages": msg_count,
            "needs_reply": needs_reply,
        })

    return conversations, total


async def get_conversation_messages(
    db: AsyncSession,
    contact_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get all messages for a contact, ordered chronologically."""
    from uuid import UUID

    stmt = (
        select(Message)
        .where(Message.contact_id == UUID(contact_id))
        .order_by(Message.date.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        {
            "id": str(msg.id),
            "direction": msg.direction,
            "date": msg.date.isoformat(),
            "content": msg.content,
            "content_length": msg.content_length,
            "is_substantive": msg.is_substantive,
            "conversation_id": msg.conversation_id,
            "synced_at": msg.synced_at.isoformat() if msg.synced_at else None,
        }
        for msg in messages
    ]


async def get_inbox_stats(db: AsyncSession) -> dict:
    """Get inbox summary stats."""
    needs_reply_ids = await _get_needs_reply_contact_ids(db)
    waiting_ids = await _get_waiting_contact_ids(db)

    # Total conversations (contacts with conversation_id messages)
    total_stmt = (
        select(func.count(func.distinct(Message.contact_id)))
        .where(Message.conversation_id.isnot(None))
    )
    total_result = await db.execute(total_stmt)
    total_conversations = total_result.scalar() or 0

    return {
        "total_conversations": total_conversations,
        "needs_reply": len(needs_reply_ids),
        "waiting_for_them": len(waiting_ids),
    }


# ── Helpers ──

async def _match_contact_by_name(
    db: AsyncSession,
    participant_name: str,
) -> Optional[Contact]:
    """
    Match a conversation participant name to an existing contact.
    Tries exact match first, then case-insensitive match.
    """
    if not participant_name:
        return None

    # Exact match
    stmt = select(Contact).where(Contact.name == participant_name)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact:
        return contact

    # Case-insensitive match
    stmt = select(Contact).where(Contact.name.ilike(participant_name))
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact:
        return contact

    return None


def _is_substantive(content: str) -> bool:
    """Check if a message is substantive (not just a quick reply)."""
    if not content:
        return False
    if len(content) < 100:
        trivial = [
            "thanks", "thank you", "congrats", "congratulations",
            "ok", "sure", "great", "awesome", "nice", "cool",
            "good", "yes", "no", "lol", "haha",
        ]
        lower = content.lower().strip().rstrip("!.")
        if lower in trivial:
            return False
    return len(content) >= 100


async def _get_needs_reply_contact_ids(db: AsyncSession) -> list:
    """Get contact IDs where the last message is from them (needs our reply)."""
    # Subquery: latest message date per contact
    latest_subq = (
        select(
            Message.contact_id,
            func.max(Message.date).label("max_date"),
        )
        .group_by(Message.contact_id)
        .subquery()
    )

    # Join to get the actual last message
    stmt = (
        select(Message.contact_id)
        .join(latest_subq, and_(
            Message.contact_id == latest_subq.c.contact_id,
            Message.date == latest_subq.c.max_date,
        ))
        .where(Message.direction == "received")
    )

    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def _get_waiting_contact_ids(db: AsyncSession) -> list:
    """Get contact IDs where the last message is from us (waiting for their reply)."""
    latest_subq = (
        select(
            Message.contact_id,
            func.max(Message.date).label("max_date"),
        )
        .group_by(Message.contact_id)
        .subquery()
    )

    stmt = (
        select(Message.contact_id)
        .join(latest_subq, and_(
            Message.contact_id == latest_subq.c.contact_id,
            Message.date == latest_subq.c.max_date,
        ))
        .where(Message.direction == "sent")
    )

    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def _update_needs_reply(db: AsyncSession) -> None:
    """Update the needs_reply flag on the latest message per contact."""
    # Get all latest messages per contact
    latest_subq = (
        select(
            Message.contact_id,
            func.max(Message.date).label("max_date"),
        )
        .group_by(Message.contact_id)
        .subquery()
    )

    stmt = (
        select(Message)
        .join(latest_subq, and_(
            Message.contact_id == latest_subq.c.contact_id,
            Message.date == latest_subq.c.max_date,
        ))
    )

    result = await db.execute(stmt)
    for msg in result.scalars().all():
        msg.needs_reply = (msg.direction == "received")


async def _update_contact_message_stats(db: AsyncSession) -> None:
    """Update contact-level message stats after sync."""
    # Get contacts with synced messages
    contacts_stmt = (
        select(func.distinct(Message.contact_id))
        .where(Message.synced_at.isnot(None))
    )
    result = await db.execute(contacts_stmt)
    contact_ids = [row[0] for row in result.all()]

    for contact_id in contact_ids:
        # Total messages
        count_stmt = select(func.count(Message.id)).where(Message.contact_id == contact_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Last message
        last_stmt = (
            select(Message)
            .where(Message.contact_id == contact_id)
            .order_by(desc(Message.date))
            .limit(1)
        )
        last_result = await db.execute(last_stmt)
        last_msg = last_result.scalar_one_or_none()

        # Update contact
        contact_stmt = select(Contact).where(Contact.id == contact_id)
        contact_result = await db.execute(contact_stmt)
        contact = contact_result.scalar_one_or_none()
        if contact:
            contact.total_messages = total
            if last_msg:
                contact.last_message_date = last_msg.date.date() if last_msg.date else None
                contact.last_message_direction = last_msg.direction
