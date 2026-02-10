"""
Follower Connector Service

Orchestrates strategic follower connection based on audience segments:
1. Scrape followers → filter out existing contacts → enrich profiles
2. Segment by scope (MujerTech, Cascadia AI, Job Target)
3. Generate personalized connection notes
4. Send connection requests

Two-phase approach: scan (preview candidates) → connect (send requests)
"""

import logging
import random
from typing import Optional

from agents import Agent, Runner, trace, set_default_openai_key
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Contact
from app.services.linkedin_browser import LinkedInBrowser, random_delay
from app.services.linkedin_voyager import LinkedInVoyager
from app.services.segmenter import (
    LATAM_LOCATIONS,
    PNW_LOCATIONS,
    AI_KEYWORDS,
    PNW_COMPANIES,
    get_target_company_names,
)


logger = logging.getLogger(__name__)
settings = get_settings()

set_default_openai_key(settings.openai_api_key)


# ============================================================================
# Connection Note Agent — short, punchy notes for connection requests
# ============================================================================

connection_note_agent = Agent(
    name="ConnectionNoteGenerator",
    instructions="""You are helping write LinkedIn connection request notes for Cristina Rodriguez, a tech professional based in Seattle.

Connection notes must be:
- VERY short (1-2 sentences, under 280 characters total)
- Personal — mention something specific about the person
- Clear about why you want to connect
- Warm and genuine, not salesy

Never use:
- Generic phrases like "I'd love to connect" or "Let's network"
- Excessive enthusiasm or exclamation points
- Corporate jargon
- Phrases like "I'd love to pick your brain"

Write as Cristina in first person. Output ONLY the note text, nothing else.""",
    model="gpt-4o",
)


# ============================================================================
# Segment Note Contexts — why Cristina wants to connect, by segment
# ============================================================================

SEGMENT_NOTE_CONTEXTS = {
    "mujertech": (
        "This person is in the MujerTech space — women entrepreneurs/tech "
        "in Latin America. Mention shared interest in Latinas in tech or "
        "community. Spanish phrases OK if the person seems Spanish-speaking."
    ),
    "cascadia": (
        "This person is in the Cascadia AI community — AI/ML professionals "
        "in the Pacific Northwest. Mention shared interest in local AI "
        "community or their specific AI work."
    ),
    "job_target": (
        "This person works at a company Cristina is interested in. Show "
        "curiosity about their work and the company, do NOT ask for jobs "
        "or referrals."
    ),
    "general": (
        "This person follows Cristina but doesn't match a specific segment. "
        "Write a friendly, genuine note based on their profile. Mention "
        "something specific about their work or background that caught your eye. "
        "Keep it natural — no need to explain why you're connecting."
    ),
}


# ============================================================================
# Helpers
# ============================================================================

def normalize_linkedin_url(url: str) -> str:
    """Normalize a LinkedIn profile URL for consistent comparison."""
    url = url.lower().strip()
    # Remove query params and hash
    url = url.split("?")[0].split("#")[0]
    # Remove trailing slash
    url = url.rstrip("/")
    # Ensure https
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)
    # Normalize to www prefix
    if "linkedin.com/in/" in url and not url.startswith("https://www.linkedin.com"):
        slug = url.split("linkedin.com/in/")[-1]
        url = f"https://www.linkedin.com/in/{slug}"
    return url


def segment_profile(
    profile: dict,
    target_companies: list[str] | None = None,
) -> list[str]:
    """
    Run segmentation on a scraped profile dict (not a Contact model).

    Uses the same keyword lists as the main segmenter but works with
    plain dicts instead of Contact objects.

    Args:
        profile: dict with name, headline, location, company, about
        target_companies: lowercase list of target company names

    Returns: list of matching segment tags
    """
    segments = []

    location = (profile.get("location") or "").lower()
    headline = (profile.get("headline") or "").lower()
    company = (profile.get("company") or "").lower()
    about = (profile.get("about") or "").lower()

    all_text = f"{location} {headline} {company} {about}"

    # MujerTech: LATAM signal in any text field
    latam_match = any(loc in all_text for loc in LATAM_LOCATIONS)
    if latam_match:
        segments.append("mujertech")

    # Cascadia AI: PNW location/company + AI keywords
    pnw_location = any(loc in location for loc in PNW_LOCATIONS)
    pnw_company = any(c in company for c in PNW_COMPANIES)
    if pnw_location or pnw_company:
        ai_text = f"{headline} {company} {about}"
        ai_match = any(kw in ai_text for kw in AI_KEYWORDS)
        if ai_match:
            segments.append("cascadia")

    # Job Target: company matches target list
    if target_companies and company:
        for target in target_companies:
            if company == target or target in company or company in target:
                segments.append("job_target")
                break

    return segments


# ============================================================================
# Connection Note Generation
# ============================================================================

async def generate_connection_note(profile: dict, segment: str) -> str:
    """
    Generate a personalized connection note for a follower (≤300 chars).

    Args:
        profile: dict with name, headline, company, location, about
        segment: the primary segment this person matched

    Returns: connection note string
    """
    prompt_parts = [
        "Write a LinkedIn connection request note for this person:",
        "",
        f"Name: {profile.get('name', 'Unknown')}",
    ]

    if profile.get("headline"):
        prompt_parts.append(f"Headline: {profile['headline']}")
    if profile.get("company"):
        prompt_parts.append(f"Company: {profile['company']}")
    if profile.get("location"):
        prompt_parts.append(f"Location: {profile['location']}")
    if profile.get("about"):
        about = profile["about"][:300]
        prompt_parts.append(f"About: {about}")

    segment_context = SEGMENT_NOTE_CONTEXTS.get(segment, "")
    if segment_context:
        prompt_parts.extend(["", f"Context: {segment_context}"])

    prompt_parts.extend([
        "",
        "They follow Cristina on LinkedIn but aren't connected yet.",
        "Write ONLY the note text. Keep it under 280 characters.",
    ])

    prompt = "\n".join(prompt_parts)

    with trace("Connection note generation"):
        result = await Runner.run(connection_note_agent, prompt)

    note = result.final_output.strip()

    # Remove quotes if the model wrapped the note in them
    if note.startswith('"') and note.endswith('"'):
        note = note[1:-1]

    # Enforce LinkedIn's 300-character limit
    if len(note) > 300:
        note = note[:297] + "..."

    return note


# ============================================================================
# Phase 1: Scan — preview candidates without sending requests
# ============================================================================

async def scan_followers(
    browser: LinkedInBrowser,
    db: AsyncSession,
    max_followers: int = 50,
    max_profiles: int = 15,
) -> dict:
    """
    Scrape followers, enrich profiles, segment them.
    Does NOT send connection requests — returns candidates for review.

    Args:
        browser: Authenticated LinkedInBrowser instance
        db: Database session
        max_followers: Max followers to scrape from the list
        max_profiles: Max profiles to enrich (limits scraping time)

    Returns:
        dict with:
            candidates: list of dicts (profile data + matched segments)
            stats: processing summary
    """
    logger.info(
        f"Starting follower scan "
        f"(max_followers={max_followers}, max_profiles={max_profiles})"
    )

    stats = {
        "followers_scraped": 0,
        "already_in_db": 0,
        "profiles_enriched": 0,
        "profiles_failed": 0,
        "matched_mujertech": 0,
        "matched_cascadia": 0,
        "matched_job_target": 0,
        "no_segment": 0,
    }

    # Step 1: Scrape followers list
    followers = await browser.scrape_followers(max_items=max_followers)
    stats["followers_scraped"] = len(followers)
    logger.info(f"Scraped {len(followers)} followers (raw)")

    if not followers:
        return {"candidates": [], "stats": stats}

    # Step 1b: Deduplicate by normalized URL (scrolling can produce repeats)
    seen_urls = set()
    unique_followers = []
    for follower in followers:
        normalized = normalize_linkedin_url(follower["profile_url"])
        if normalized not in seen_urls:
            seen_urls.add(normalized)
            unique_followers.append(follower)

    dupes_removed = len(followers) - len(unique_followers)
    if dupes_removed:
        logger.info(f"Removed {dupes_removed} duplicate followers")
    followers = unique_followers

    # Step 1c: Filter out own profile (shows up in page header/nav)
    # Strategy 1: try to get own profile URL from the browser page
    own_profile_url = await browser.get_own_profile_url()
    if own_profile_url:
        own_normalized = normalize_linkedin_url(own_profile_url)
        before = len(followers)
        followers = [
            f for f in followers
            if normalize_linkedin_url(f["profile_url"]) != own_normalized
        ]
        self_removed = before - len(followers)
        if self_removed:
            logger.info(f"Filtered out {self_removed} own profile entries (by URL)")

    # Strategy 2: filter out any profile URL that appears 3+ times
    # (own profile link appears on every page load, real followers appear once)
    from collections import Counter
    url_counts = Counter(
        normalize_linkedin_url(f["profile_url"]) for f in followers
    )
    repeated_urls = {url for url, count in url_counts.items() if count >= 3}
    if repeated_urls:
        before = len(followers)
        seen_repeated = set()
        filtered = []
        for f in followers:
            norm = normalize_linkedin_url(f["profile_url"])
            if norm in repeated_urls:
                if norm not in seen_repeated:
                    seen_repeated.add(norm)
                    # Skip entirely — if it appears 3+ times it's the user's own profile
            else:
                filtered.append(f)
        followers = filtered
        logger.info(f"Filtered out {before - len(followers)} repeated profile entries")

    stats["followers_scraped"] = len(followers)

    # Step 2: Get existing contact URLs from DB for filtering
    stmt = select(Contact.linkedin_url)
    result = await db.execute(stmt)
    existing_urls = {
        normalize_linkedin_url(url)
        for url in result.scalars().all()
        if url
    }

    # Get target companies for job_target segmentation
    target_companies = await get_target_company_names(db)

    # Step 3: Filter out existing contacts
    new_followers = []
    for follower in followers:
        normalized = normalize_linkedin_url(follower["profile_url"])
        if normalized in existing_urls:
            stats["already_in_db"] += 1
        else:
            new_followers.append(follower)

    logger.info(
        f"{len(new_followers)} new followers (not in DB), "
        f"{stats['already_in_db']} already known"
    )

    # Step 4: Enrich profiles via Voyager API (fast, ~1s per profile)
    candidates = []
    profiles_to_enrich = new_followers[:max_profiles]

    voyager = LinkedInVoyager()
    try:
        await voyager.start()
        voyager_ok = await voyager.is_authenticated()
        if not voyager_ok:
            logger.warning("Voyager API auth failed, will fall back to browser scraping")
    except Exception as e:
        logger.warning(f"Voyager API init failed: {e}, will fall back to browser scraping")
        voyager_ok = False

    for i, follower in enumerate(profiles_to_enrich):
        logger.info(
            f"Enriching profile {i+1}/{len(profiles_to_enrich)}: "
            f"{follower['name']}"
        )

        profile = None

        # Try Voyager API first (fast path: ~1s)
        if voyager_ok:
            profile = await voyager.get_profile(follower["profile_url"])

        # Fall back to Playwright browser scraping (slow path: ~10s)
        if not profile:
            logger.info(f"  Falling back to browser scrape for {follower['name']}")
            profile = await browser.scrape_profile(follower["profile_url"])

        if not profile:
            logger.warning(f"Failed to enrich profile: {follower['profile_url']}")
            stats["profiles_failed"] += 1
            continue

        stats["profiles_enriched"] += 1

        # Step 5: Segment using the enriched profile data
        segments = segment_profile(profile, target_companies)

        if segments:
            for seg in segments:
                stats[f"matched_{seg}"] += 1
            logger.info(f"  Matched segments: {segments}")
        else:
            stats["no_segment"] += 1
            logger.debug(f"  No segment match")

        candidates.append({
            "name": profile.get("name") or follower["name"],
            "headline": profile.get("headline") or follower.get("headline", ""),
            "profile_url": follower["profile_url"],
            "location": profile.get("location", ""),
            "company": profile.get("company", ""),
            "about": profile.get("about", ""),
            "segments": segments,
        })

        # Light rate limit for Voyager (short delay to avoid detection)
        if voyager_ok and i < len(profiles_to_enrich) - 1:
            await random_delay(0.5, 1.5)
        elif i < len(profiles_to_enrich) - 1:
            await random_delay(1.0, 2.5)

    # Clean up Voyager client
    await voyager.stop()

    logger.info(
        f"Scan complete: {len(candidates)} candidates "
        f"(mujertech={stats['matched_mujertech']}, "
        f"cascadia={stats['matched_cascadia']}, "
        f"job_target={stats['matched_job_target']})"
    )

    return {"candidates": candidates, "stats": stats}


# ============================================================================
# Phase 2: Generate Notes — create personalized notes for user review
# ============================================================================

async def generate_notes_for_candidates(candidates: list[dict]) -> list[dict]:
    """
    Generate personalized connection notes for candidates.
    Returns candidates with a "note" field added.
    Does NOT send anything — just generates notes for user review.
    """
    logger.info(f"Generating notes for {len(candidates)} candidates")

    results = []
    for i, candidate in enumerate(candidates):
        primary_segment = candidate["segments"][0] if candidate["segments"] else "general"

        try:
            note = await generate_connection_note(candidate, primary_segment)
            logger.info(f"  Note for {candidate['name']} ({len(note)} chars): {note[:60]}...")
        except Exception as e:
            logger.error(f"  Note generation failed for {candidate['name']}: {e}")
            note = ""

        results.append({
            **candidate,
            "note": note,
        })

    return results


# ============================================================================
# Phase 3: Connect — send requests with user-approved notes
# ============================================================================

async def connect_with_candidates(
    browser: LinkedInBrowser,
    candidates: list[dict],
    max_connections: int = 10,
) -> dict:
    """
    Send connection requests with pre-approved notes.

    Candidates must already have a "note" field (from generate_notes_for_candidates
    or edited by the user). No note generation happens here.

    Args:
        browser: Authenticated LinkedInBrowser instance
        candidates: list of candidate dicts with "note" field
        max_connections: Max requests per run (safety limit)

    Returns:
        dict with:
            results: list of per-candidate outcomes
            stats: summary counts
    """
    logger.info(
        f"Starting connection run "
        f"({len(candidates)} candidates, max={max_connections})"
    )

    to_connect = candidates[:max_connections]
    results = []
    stats = {
        "total": len(to_connect),
        "sent": 0,
        "already_connected": 0,
        "already_pending": 0,
        "failed": 0,
        "note_not_supported": 0,
    }

    for i, candidate in enumerate(to_connect):
        logger.info(f"Processing {i+1}/{len(to_connect)}: {candidate['name']}")

        note = candidate.get("note", "")

        # Send the connection request
        result = await browser.send_connection_request(
            profile_url=candidate["profile_url"],
            note=note,
        )

        # Enrich the result with candidate info
        result["name"] = candidate["name"]
        result["segments"] = candidate["segments"]
        result["note_sent"] = note

        # If note couldn't be added, include it for manual action
        if result["status"] == "note_not_supported":
            result["note_for_manual"] = note

        results.append(result)

        status = result["status"]
        if status in stats:
            stats[status] += 1

        logger.info(f"  Result: {status}")

        # Rate limit between connection requests (longer delays for safety)
        if i < len(to_connect) - 1:
            await random_delay(15.0, 30.0)

    logger.info(
        f"Connection run complete: {stats['sent']} sent, "
        f"{stats['failed']} failed, "
        f"{stats['already_connected']} already connected"
    )

    return {"results": results, "stats": stats}
