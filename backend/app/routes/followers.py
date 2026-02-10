"""
Follower connection routes — scan followers, segment them, and connect strategically.

Flow:
1. POST /api/followers/scan            → scrape followers, enrich, segment → candidates
2. POST /api/followers/generate-notes  → generate personalized notes for user review
3. POST /api/followers/connect         → send connection requests with approved notes
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.followers import (
    ScanRequest,
    ScanResponse,
    GenerateNotesRequest,
    GenerateNotesResponse,
    ConnectRequest,
    ConnectResponse,
)
from app.services.linkedin_browser import LinkedInBrowser
from app.services.follower_connector import (
    scan_followers,
    generate_notes_for_candidates,
    connect_with_candidates,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/followers", tags=["followers"])


async def get_authenticated_browser() -> LinkedInBrowser:
    """
    Start a browser and verify LinkedIn authentication.
    Raises HTTPException if not authenticated.
    Returns an open browser — caller must call browser.stop() when done.
    Uses headless=False because LinkedIn blocks headless Chromium.
    """
    browser = LinkedInBrowser()
    await browser.start(headless=False)

    if not await browser.is_logged_in():
        await browser.stop()
        raise HTTPException(
            status_code=401,
            detail=(
                "LinkedIn session not authenticated. "
                "Run the manual login script first: "
                "uv run python test_auth.py"
            ),
        )

    return browser


@router.post("/scan", response_model=ScanResponse)
async def scan_followers_route(
    request: ScanRequest = ScanRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan your LinkedIn followers, enrich their profiles, and segment them.
    Returns candidates — does NOT send connection requests.
    """
    browser = await get_authenticated_browser()

    try:
        result = await scan_followers(
            browser=browser,
            db=db,
            max_followers=request.max_followers,
            max_profiles=request.max_profiles,
        )
        return result
    except Exception as e:
        logger.error(f"Follower scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}")
    finally:
        await browser.stop()


@router.post("/generate-notes", response_model=GenerateNotesResponse)
async def generate_notes_route(request: GenerateNotesRequest):
    """
    Generate personalized connection notes for selected candidates.
    Returns candidates with notes for user review/editing.
    Does NOT send any connection requests.
    """
    if not request.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    try:
        candidates_dicts = [c.model_dump() for c in request.candidates]
        results = await generate_notes_for_candidates(candidates_dicts)
        return {"candidates": results}
    except Exception as e:
        logger.error(f"Note generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Note generation failed: {e}")


@router.post("/connect", response_model=ConnectResponse)
async def connect_followers_route(request: ConnectRequest):
    """
    Send connection requests with user-reviewed notes.

    Expects candidates with "note" field (from /generate-notes, possibly edited).
    Does NOT generate notes — just sends the requests.
    """
    if not request.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    browser = await get_authenticated_browser()

    try:
        candidates_dicts = [c.model_dump() for c in request.candidates]

        result = await connect_with_candidates(
            browser=browser,
            candidates=candidates_dicts,
            max_connections=request.max_connections,
        )
        return result
    except Exception as e:
        logger.error(f"Follower connect failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connect failed: {e}")
    finally:
        await browser.stop()
