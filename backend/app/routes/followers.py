"""
Follower connection routes — scan followers, segment them, and connect strategically.

Flow:
1. POST /api/followers/scan            → scrape followers, enrich, segment → candidates
2. POST /api/followers/generate-notes  → generate personalized notes for user review
3. POST /api/followers/connect         → send connection requests with approved notes
4. GET  /api/followers/requests        → list past connection requests
5. POST /api/followers/check-acceptances → check if pending requests were accepted
6. GET  /api/followers/requests/stats  → acceptance rate by segment
"""

import logging
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.connection_request import ConnectionRequest
from app.models.contact import Contact
from app.schemas.followers import (
    ScanRequest,
    ScanResponse,
    GenerateNotesRequest,
    GenerateNotesResponse,
    ConnectRequest,
    ConnectResponse,
    TrackRequest,
    TrackResponse,
)
from app.schemas.connection_requests import (
    ConnectionRequestOut,
    ConnectionRequestListResponse,
    CheckAcceptancesResponse,
    SegmentAcceptanceStats,
    ConnectionRequestStatsResponse,
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
async def connect_followers_route(
    request: ConnectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send connection requests with user-reviewed notes.
    Saves each result to the connection_requests table for tracking.
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

        # Save each result to the database
        for r in result["results"]:
            matching_candidate = next(
                (c for c in candidates_dicts if c["profile_url"] == r["profile_url"]),
                None,
            )

            db_status = r["status"]
            if db_status == "sent":
                db_status = "pending"

            connection_request = ConnectionRequest(
                profile_url=r["profile_url"],
                name=r.get("name", matching_candidate["name"] if matching_candidate else ""),
                headline=matching_candidate.get("headline", "") if matching_candidate else "",
                company=matching_candidate.get("company", "") if matching_candidate else "",
                location=matching_candidate.get("location", "") if matching_candidate else "",
                segments=r.get("segments", []),
                note_sent=r.get("note_sent", ""),
                status=db_status,
            )
            db.add(connection_request)

        await db.commit()
        logger.info(f"Saved {len(result['results'])} connection requests to database")

        return result
    except Exception as e:
        logger.error(f"Follower connect failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connect failed: {e}")
    finally:
        await browser.stop()


@router.post("/track", response_model=TrackResponse)
async def track_connection_requests(
    request: TrackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Save manually-sent connection requests for tracking.
    No browser automation — just records that the user sent these requests.
    """
    if not request.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    for candidate in request.candidates:
        connection_request = ConnectionRequest(
            profile_url=candidate.profile_url,
            name=candidate.name,
            headline=candidate.headline or "",
            company=candidate.company or "",
            location=candidate.location or "",
            segments=candidate.segments,
            note_sent=candidate.note or "",
            status="pending",
        )
        db.add(connection_request)

    await db.commit()
    logger.info(f"Tracked {len(request.candidates)} manually-sent connection requests")

    return TrackResponse(saved=len(request.candidates))


@router.get("/requests", response_model=ConnectionRequestListResponse)
async def list_connection_requests(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all past connection requests, optionally filtered by status.
    """
    query = select(ConnectionRequest).order_by(ConnectionRequest.sent_at.desc())

    if status:
        query = query.where(ConnectionRequest.status == status)

    result = await db.execute(query)
    requests = result.scalars().all()

    return ConnectionRequestListResponse(
        requests=[ConnectionRequestOut.model_validate(r) for r in requests],
        total=len(requests),
    )


@router.post("/check-acceptances", response_model=CheckAcceptancesResponse)
async def check_acceptances(db: AsyncSession = Depends(get_db)):
    """
    Check if any pending connection requests have been accepted.
    Compares pending requests against the contacts table —
    if a profile_url exists in contacts, the request was accepted.
    """
    pending_query = select(ConnectionRequest).where(
        ConnectionRequest.status == "pending"
    )
    result = await db.execute(pending_query)
    pending_requests = result.scalars().all()

    if not pending_requests:
        return CheckAcceptancesResponse(
            checked=0, newly_accepted=0, still_pending=0, accepted_names=[]
        )

    contacts_query = select(Contact.linkedin_url)
    contacts_result = await db.execute(contacts_query)
    contact_urls = {row[0] for row in contacts_result.all()}

    newly_accepted = 0
    accepted_names: list[str] = []
    now = datetime.utcnow()

    for req in pending_requests:
        req_url = req.profile_url.rstrip("/")
        matched = any(
            contact_url.rstrip("/") == req_url for contact_url in contact_urls
        )

        if matched:
            req.status = "accepted"
            req.accepted_at = now
            newly_accepted += 1
            accepted_names.append(req.name)

    await db.commit()

    still_pending = len(pending_requests) - newly_accepted

    logger.info(
        f"Acceptance check: {newly_accepted} accepted, "
        f"{still_pending} still pending"
    )

    return CheckAcceptancesResponse(
        checked=len(pending_requests),
        newly_accepted=newly_accepted,
        still_pending=still_pending,
        accepted_names=accepted_names,
    )


@router.get("/requests/stats", response_model=ConnectionRequestStatsResponse)
async def connection_request_stats(db: AsyncSession = Depends(get_db)):
    """
    Get acceptance rate stats, overall and by segment.
    """
    result = await db.execute(select(ConnectionRequest))
    all_requests = result.scalars().all()

    if not all_requests:
        return ConnectionRequestStatsResponse(
            total_requests=0,
            total_accepted=0,
            total_pending=0,
            total_failed=0,
            overall_acceptance_rate=0.0,
            by_segment=[],
        )

    total = len(all_requests)
    accepted = sum(1 for r in all_requests if r.status == "accepted")
    pending = sum(1 for r in all_requests if r.status == "pending")
    failed = sum(
        1 for r in all_requests
        if r.status in ("failed", "already_connected", "already_pending")
    )

    resolved = accepted + failed
    overall_rate = (accepted / resolved * 100) if resolved > 0 else 0.0

    segment_data: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total_sent": 0, "accepted": 0, "pending": 0, "failed": 0}
    )

    for req in all_requests:
        segments = req.segments or ["general"]
        for seg in segments:
            segment_data[seg]["total_sent"] += 1
            if req.status == "accepted":
                segment_data[seg]["accepted"] += 1
            elif req.status == "pending":
                segment_data[seg]["pending"] += 1
            else:
                segment_data[seg]["failed"] += 1

    by_segment = []
    for seg_name, counts in sorted(segment_data.items()):
        seg_resolved = counts["accepted"] + counts["failed"]
        rate = (counts["accepted"] / seg_resolved * 100) if seg_resolved > 0 else 0.0
        by_segment.append(
            SegmentAcceptanceStats(
                segment=seg_name,
                total_sent=counts["total_sent"],
                accepted=counts["accepted"],
                pending=counts["pending"],
                failed=counts["failed"],
                acceptance_rate=round(rate, 1),
            )
        )

    return ConnectionRequestStatsResponse(
        total_requests=total,
        total_accepted=accepted,
        total_pending=pending,
        total_failed=failed,
        overall_acceptance_rate=round(overall_rate, 1),
        by_segment=by_segment,
    )
