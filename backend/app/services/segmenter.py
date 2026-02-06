"""
Audience Segmentation Service

Auto-tags contacts into segments based on location, role, and company.
Three segments: MujerTech, Cascadia AI, Job Search (target companies).
"""

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, TargetCompany


# ============================================================================
# MujerTech Segment - Women entrepreneurs in LATAM
# ============================================================================

LATAM_LOCATIONS = [
    # Countries
    "mexico", "méxico", "colombia", "argentina", "chile", "peru", "perú",
    "ecuador", "venezuela", "guatemala", "cuba", "bolivia",
    "dominican republic", "república dominicana", "honduras", "paraguay",
    "el salvador", "nicaragua", "costa rica", "panama", "panamá", "uruguay",
    "puerto rico",
    # Regions
    "latam", "latin america", "américa latina", "latinoamérica",
    "south america", "central america", "sudamérica", "centroamérica",
    # Major cities
    "mexico city", "ciudad de méxico", "cdmx", "bogotá", "bogota",
    "buenos aires", "santiago", "lima", "quito", "caracas", "montevideo",
    "san josé", "san jose", "guatemala city", "tegucigalpa", "san salvador",
    "managua", "panamá city", "panama city", "santo domingo", "havana",
    "la habana", "asunción", "asuncion", "la paz", "sucre",
    "medellín", "medellin", "cartagena", "cali", "barranquilla",
    "guadalajara", "monterrey", "tijuana", "cancún", "cancun",
    "córdoba", "cordoba", "rosario", "mendoza",
    "valparaíso", "valparaiso", "concepción", "concepcion",
    "arequipa", "trujillo", "cusco", "cuzco",
    "guayaquil", "cuenca",
    "maracaibo", "valencia", "barquisimeto",
]

ENTREPRENEUR_KEYWORDS = [
    # English
    "entrepreneur", "founder", "co-founder", "cofounder",
    "owner", "ceo", "chief executive",
    "small business", "startup", "start-up", "my own",
    "self-employed", "freelance", "independent",
    "solopreneur", "business owner",
    # Spanish
    "emprendedor", "emprendedora", "fundador", "fundadora",
    "cofundador", "cofundadora", "dueño", "dueña",
    "negocio propio", "mi empresa", "mi negocio",
    "empresario", "empresaria", "autónomo", "autónoma",
    "independiente", "cuenta propia",
]


def is_mujertech_candidate(contact: Contact) -> bool:
    """
    Check if contact matches MujerTech segment criteria.

    Matches if:
    - Location is in LATAM, OR
    - Role/headline contains entrepreneur keywords AND location suggests Spanish-speaking
    """
    location = (contact.location or "").lower()
    headline = (contact.headline or "").lower()
    position = (contact.position or "").lower()
    company = (contact.company or "").lower()

    # Check location for LATAM
    location_match = any(loc in location for loc in LATAM_LOCATIONS)

    # Check for entrepreneur keywords in headline/position
    text_to_check = f"{headline} {position} {company}"
    entrepreneur_match = any(kw in text_to_check for kw in ENTREPRENEUR_KEYWORDS)

    # Match if in LATAM location, or entrepreneur with some LATAM indicator
    if location_match:
        return True

    # If entrepreneur, also check if name or other signals suggest LATAM connection
    # (This is a softer match - entrepreneurs anywhere could be interested)
    if entrepreneur_match and location_match:
        return True

    return False


# ============================================================================
# Cascadia AI Segment - Pacific Northwest AI community
# ============================================================================

PNW_LOCATIONS = [
    # Washington
    "seattle", "washington", ", wa", "bellevue", "redmond", "kirkland",
    "tacoma", "spokane", "olympia", "everett", "renton", "kent",
    "federal way", "yakima", "bellingham", "vancouver, wa",
    # Oregon
    "portland", "oregon", ", or", "eugene", "salem", "bend", "corvallis",
    "beaverton", "hillsboro", "gresham", "medford",
    # British Columbia
    "vancouver", "british columbia", ", bc", "victoria", "burnaby",
    "surrey", "richmond", "kelowna", "vancouver, bc",
    # Region names
    "pacific northwest", "pnw", "puget sound", "cascadia",
]

AI_KEYWORDS = [
    # Core AI/ML
    "artificial intelligence", "machine learning", "deep learning",
    "ai ", " ai", "ai/ml", "ml ", " ml",
    "neural network", "computer vision", "nlp",
    "natural language processing", "natural language",
    # Models & Tech
    "llm", "large language model", "gpt", "transformer",
    "generative ai", "gen ai", "genai",
    "chatgpt", "claude", "anthropic", "openai",
    "langchain", "hugging face", "huggingface",
    # Data Science adjacent
    "data science", "data scientist", "ml engineer",
    "machine learning engineer", "ai engineer",
    "ai researcher", "ml researcher", "research scientist",
    # Specific domains
    "reinforcement learning", "computer vision",
    "speech recognition", "recommendation system",
    "predictive model", "tensorflow", "pytorch",
]


def is_cascadia_candidate(contact: Contact) -> bool:
    """
    Check if contact matches Cascadia AI segment criteria.

    Matches if:
    - Location is in Pacific Northwest AND
    - Headline/position contains AI/ML keywords
    """
    location = (contact.location or "").lower()
    headline = (contact.headline or "").lower()
    position = (contact.position or "").lower()
    company = (contact.company or "").lower()
    about = (contact.about or "").lower()

    # Must be in PNW
    location_match = any(loc in location for loc in PNW_LOCATIONS)

    if not location_match:
        return False

    # Must have AI/ML keywords
    text_to_check = f"{headline} {position} {company} {about}"
    ai_match = any(kw in text_to_check for kw in AI_KEYWORDS)

    return ai_match


# ============================================================================
# Job Search Segment - People at target companies
# ============================================================================

async def get_target_company_names(db: AsyncSession) -> list[str]:
    """Get list of target company names (lowercase for matching)."""
    stmt = select(TargetCompany.name)
    result = await db.execute(stmt)
    names = result.scalars().all()
    return [name.lower() for name in names]


def is_job_search_candidate(contact: Contact, target_companies: list[str]) -> bool:
    """
    Check if contact matches Job Search segment criteria.

    Matches if:
    - Contact's company matches a target company name
    """
    if not target_companies:
        return False

    company = (contact.company or "").lower()

    if not company:
        return False

    # Check for exact or partial match
    for target in target_companies:
        # Exact match
        if company == target:
            return True
        # Company contains target name (e.g., "Google" in "Google Cloud")
        if target in company:
            return True
        # Target contains company name (e.g., "Stripe" matches "Stripe, Inc.")
        if company in target:
            return True

    return False


# ============================================================================
# Main Segmentation Functions
# ============================================================================

async def segment_contact(
    db: AsyncSession,
    contact: Contact,
    target_companies: Optional[list[str]] = None,
) -> list[str]:
    """
    Determine which segments a contact belongs to.

    Returns list of segment tags.
    """
    segments = []

    # Check MujerTech
    if is_mujertech_candidate(contact):
        segments.append("mujertech")

    # Check Cascadia
    if is_cascadia_candidate(contact):
        segments.append("cascadia")

    # Check Job Search (requires target companies list)
    if target_companies is None:
        target_companies = await get_target_company_names(db)

    if is_job_search_candidate(contact, target_companies):
        segments.append("job_target")

    return segments


async def update_contact_segments(
    db: AsyncSession,
    contact: Contact,
    target_companies: Optional[list[str]] = None,
) -> list[str]:
    """
    Update a contact's segment tags.

    Returns the new segment tags.
    """
    segments = await segment_contact(db, contact, target_companies)
    contact.segment_tags = segments if segments else None
    return segments


async def segment_all_contacts(db: AsyncSession) -> dict:
    """
    Run segmentation on all contacts.

    Returns dict with processing stats.
    """
    result = {
        "contacts_processed": 0,
        "mujertech_count": 0,
        "cascadia_count": 0,
        "job_target_count": 0,
        "no_segment_count": 0,
    }

    # Get target companies once
    target_companies = await get_target_company_names(db)

    # Get all contacts
    stmt = select(Contact)
    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        segments = await update_contact_segments(db, contact, target_companies)
        result["contacts_processed"] += 1

        if "mujertech" in segments:
            result["mujertech_count"] += 1
        if "cascadia" in segments:
            result["cascadia_count"] += 1
        if "job_target" in segments:
            result["job_target_count"] += 1
        if not segments:
            result["no_segment_count"] += 1

    await db.commit()

    return result


async def segment_contacts_without_tags(db: AsyncSession) -> dict:
    """
    Run segmentation only on contacts without existing segment tags.
    More efficient for incremental updates.

    Returns dict with processing stats.
    """
    result = {
        "contacts_processed": 0,
        "mujertech_count": 0,
        "cascadia_count": 0,
        "job_target_count": 0,
        "no_segment_count": 0,
    }

    # Get target companies once
    target_companies = await get_target_company_names(db)

    # Get contacts without segment tags
    stmt = select(Contact).where(Contact.segment_tags.is_(None))
    contacts_result = await db.execute(stmt)
    contacts = contacts_result.scalars().all()

    for contact in contacts:
        segments = await update_contact_segments(db, contact, target_companies)
        result["contacts_processed"] += 1

        if "mujertech" in segments:
            result["mujertech_count"] += 1
        if "cascadia" in segments:
            result["cascadia_count"] += 1
        if "job_target" in segments:
            result["job_target_count"] += 1
        if not segments:
            result["no_segment_count"] += 1

    await db.commit()

    return result
