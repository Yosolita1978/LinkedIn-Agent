"""
Message Generator Service

Uses Claude API to generate personalized outreach messages based on:
- Contact profile and history
- Segment (MujerTech, Cascadia, Job Search)
- Resurrection hooks (if any)
- Outreach purpose
"""

from typing import Optional
from datetime import datetime

import anthropic
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Contact, Message, ResurrectionOpportunity


settings = get_settings()

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ============================================================================
# Prompt Templates
# ============================================================================

SYSTEM_PROMPT = """You are helping write LinkedIn messages for Cristina Rodriguez, a tech professional based in Seattle.

Your messages should be:
- Warm and authentic, not salesy or generic
- Concise (2-4 sentences for initial outreach, can be longer for follow-ups)
- Personal - reference specific details about the person when available
- Action-oriented - include a clear but soft call to action
- Professional but friendly

Never use:
- Generic openers like "I hope this message finds you well"
- Overly formal language
- Excessive exclamation points
- Buzzwords or corporate jargon
- Phrases like "I'd love to pick your brain"

Always write in first person as Cristina."""


SEGMENT_CONTEXTS = {
    "mujertech": """Context: This contact is part of the MujerTech community - women entrepreneurs and tech professionals in Latin America. Cristina runs this community to connect and support Latinas in tech.

Tone: Warm, supportive, community-focused. Can use Spanish phrases naturally if appropriate. Focus on mutual support and community connection.""",

    "cascadia": """Context: This contact is part of the Cascadia AI community - AI/ML professionals in the Pacific Northwest (Seattle, Portland, Vancouver). Cristina is building this community to connect local AI practitioners.

Tone: Professional but friendly, tech-savvy. Focus on local AI community, knowledge sharing, and professional connection.""",

    "job_target": """Context: This contact works at a company where Cristina is interested in opportunities. This is a networking message, not a job application.

Tone: Professional, curious about their work. Focus on learning about their experience at the company, not asking for referrals directly.""",
}


PURPOSE_TEMPLATES = {
    "reconnect": "Goal: Reconnect with this contact after a period of no communication. Reference your shared history if available.",

    "introduce": "Goal: Make a first meaningful connection. Find common ground and express genuine interest.",

    "follow_up": "Goal: Follow up on a previous conversation or commitment. Be specific about what was discussed.",

    "invite_community": "Goal: Invite them to join a community or event. Explain the value without being pushy.",

    "ask_advice": "Goal: Ask for their perspective or advice on something specific. Be clear about what you're asking.",

    "congratulate": "Goal: Congratulate them on a recent achievement (new job, promotion, milestone). Be genuine and brief.",

    "share_resource": "Goal: Share something valuable with them (article, opportunity, connection). Explain why you thought of them.",
}


# ============================================================================
# Context Building
# ============================================================================

async def build_contact_context(db: AsyncSession, contact: Contact) -> str:
    """Build context string about the contact for the prompt."""
    context_parts = []

    # Basic info
    context_parts.append(f"Name: {contact.name}")

    if contact.headline:
        context_parts.append(f"Headline: {contact.headline}")

    if contact.company:
        context_parts.append(f"Company: {contact.company}")

    if contact.position:
        context_parts.append(f"Position: {contact.position}")

    if contact.location:
        context_parts.append(f"Location: {contact.location}")

    if contact.about:
        # Truncate if too long
        about = contact.about[:500] + "..." if len(contact.about) > 500 else contact.about
        context_parts.append(f"About: {about}")

    # Warmth and relationship
    if contact.warmth_score:
        context_parts.append(f"Relationship warmth: {contact.warmth_score}/100")

    if contact.total_messages:
        context_parts.append(f"Total messages exchanged: {contact.total_messages}")

    if contact.last_message_date:
        days_since = (datetime.utcnow().date() - contact.last_message_date).days
        context_parts.append(f"Last message: {days_since} days ago")

    if contact.connection_date:
        context_parts.append(f"Connected since: {contact.connection_date}")

    return "\n".join(context_parts)


async def get_recent_messages(db: AsyncSession, contact_id, limit: int = 5) -> str:
    """Get recent message history for context."""
    stmt = select(Message).where(
        Message.contact_id == contact_id
    ).order_by(desc(Message.date)).limit(limit)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        return "No previous messages."

    # Reverse to chronological order
    messages = list(reversed(messages))

    history_parts = ["Recent conversation:"]
    for msg in messages:
        direction = "You" if msg.direction == "sent" else "Them"
        content = msg.content[:200] + "..." if msg.content and len(msg.content) > 200 else msg.content
        date_str = msg.date.strftime("%Y-%m-%d")
        history_parts.append(f"[{date_str}] {direction}: {content or '(no content)'}")

    return "\n".join(history_parts)


async def get_resurrection_context(db: AsyncSession, contact_id) -> Optional[str]:
    """Get active resurrection hooks for the contact."""
    stmt = select(ResurrectionOpportunity).where(
        ResurrectionOpportunity.contact_id == contact_id,
        ResurrectionOpportunity.is_active == True,
    )

    result = await db.execute(stmt)
    opportunities = result.scalars().all()

    if not opportunities:
        return None

    hook_descriptions = {
        "dormant": "This is a warm relationship that has gone quiet. Good opportunity to reconnect.",
        "promise_made": "You made a commitment that wasn't followed up on.",
        "question_unanswered": "They asked you a question that wasn't answered.",
        "they_waiting": "Their last message was to you - the ball is in your court.",
    }

    hooks = []
    for opp in opportunities:
        desc = hook_descriptions.get(opp.hook_type, "")
        hooks.append(f"- {desc}\n  Detail: {opp.hook_detail}")

    return "Outreach hooks:\n" + "\n".join(hooks)


# ============================================================================
# Message Generation
# ============================================================================

async def generate_message(
    db: AsyncSession,
    contact_id: str,
    purpose: str = "reconnect",
    segment: Optional[str] = None,
    custom_context: Optional[str] = None,
    num_variations: int = 2,
) -> dict:
    """
    Generate personalized outreach message(s) for a contact.

    Args:
        db: Database session
        contact_id: UUID of the contact
        purpose: Type of outreach (reconnect, introduce, follow_up, etc.)
        segment: Override segment (mujertech, cascadia, job_target)
        custom_context: Additional context to include
        num_variations: Number of message variations to generate (1-3)

    Returns:
        Dict with contact info and generated messages
    """
    from uuid import UUID

    # Get contact
    stmt = select(Contact).where(Contact.id == UUID(contact_id))
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()

    if not contact:
        raise ValueError(f"Contact not found: {contact_id}")

    # Determine segment
    if not segment and contact.segment_tags:
        segment = contact.segment_tags[0]  # Use first segment

    # Build prompt components
    contact_context = await build_contact_context(db, contact)
    message_history = await get_recent_messages(db, contact.id)
    resurrection_context = await get_resurrection_context(db, contact.id)

    # Build the full prompt
    prompt_parts = [
        "## Contact Information",
        contact_context,
        "",
        "## Message History",
        message_history,
    ]

    if resurrection_context:
        prompt_parts.extend(["", "## Outreach Opportunity", resurrection_context])

    if segment and segment in SEGMENT_CONTEXTS:
        prompt_parts.extend(["", "## Segment Context", SEGMENT_CONTEXTS[segment]])

    if purpose in PURPOSE_TEMPLATES:
        prompt_parts.extend(["", "## Purpose", PURPOSE_TEMPLATES[purpose]])

    if custom_context:
        prompt_parts.extend(["", "## Additional Context", custom_context])

    prompt_parts.extend([
        "",
        f"## Task",
        f"Write {num_variations} different LinkedIn message variation(s) for this contact.",
        "Each variation should take a slightly different angle or tone.",
        "Format: Number each variation (1, 2, etc.) and separate with blank lines.",
        "Keep messages concise - aim for 2-4 sentences for initial outreach.",
    ])

    user_prompt = "\n".join(prompt_parts)

    # Call Claude API
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    # Parse response
    raw_response = response.content[0].text

    # Simple parsing - split by numbered variations
    variations = []
    current_variation = []

    for line in raw_response.split("\n"):
        # Check if this line starts a new variation (e.g., "1.", "2.", "1)", "2)")
        stripped = line.strip()
        if stripped and (
            (stripped[0].isdigit() and len(stripped) > 1 and stripped[1] in ".)")
            or stripped.startswith("Variation")
        ):
            if current_variation:
                variations.append("\n".join(current_variation).strip())
                current_variation = []
            # Don't include the number prefix in the variation
            if stripped[0].isdigit() and stripped[1] in ".)":
                current_variation.append(stripped[2:].strip())
            elif ":" in stripped:
                current_variation.append(stripped.split(":", 1)[1].strip())
        else:
            current_variation.append(line)

    if current_variation:
        variations.append("\n".join(current_variation).strip())

    # Clean up variations
    variations = [v.strip() for v in variations if v.strip()]

    # If parsing failed, return the whole response as one variation
    if not variations:
        variations = [raw_response.strip()]

    return {
        "contact": {
            "id": str(contact.id),
            "name": contact.name,
            "company": contact.company,
            "headline": contact.headline,
            "warmth_score": contact.warmth_score,
        },
        "purpose": purpose,
        "segment": segment,
        "variations": variations,
        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
    }


async def generate_batch_messages(
    db: AsyncSession,
    contact_ids: list[str],
    purpose: str = "reconnect",
    segment: Optional[str] = None,
) -> list[dict]:
    """
    Generate messages for multiple contacts.

    Returns list of generation results.
    """
    results = []

    for contact_id in contact_ids:
        try:
            result = await generate_message(
                db=db,
                contact_id=contact_id,
                purpose=purpose,
                segment=segment,
                num_variations=1,  # Single variation for batch
            )
            results.append(result)
        except Exception as e:
            results.append({
                "contact_id": contact_id,
                "error": str(e),
            })

    return results
