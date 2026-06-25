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
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
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
    profile_identity_key,
)
from app.services.message_generator import generate_message
from app.services.queue_service import add_to_queue


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


def _key_or_none(url: str) -> str | None:
    """Stable identity key for matching, or None if the URL is malformed."""
    try:
        return profile_identity_key(url)
    except ValueError:
        logger.warning(f"URL has no /in/ identity segment: {url}")
        return None


@router.post("/check-acceptances", response_model=CheckAcceptancesResponse)
async def check_acceptances(db: AsyncSession = Depends(get_db)):
    """
    Detect accepted connection requests and bridge them into a conversation.

    Two guarded, idempotent transitions (both atomic compare-and-set under
    Postgres READ COMMITTED — a conditional UPDATE blocks the racing session,
    which then re-reads and matches 0 rows):

      1. pending → accepted              (acceptance detected: the person now
                                          exists in the contacts table)
      2. accepted → conversation_queued  (only the winner of this CAS generates
                                          a first-touch message and queues it)

    A re-run is a no-op for already-queued rows, and picks up any 'accepted'
    straggler left behind by a crashed earlier run.
    """
    now = datetime.utcnow()

    # Map every contact to its stable identity key → contact id.
    contacts_result = await db.execute(select(Contact.id, Contact.linkedin_url))
    contact_id_by_key: dict[str, object] = {}
    for cid, url in contacts_result.all():
        key = _key_or_none(url) if url else None
        if key:
            contact_id_by_key[key] = cid

    # ── Transition 1: detect acceptances (pending → accepted) ──
    pending_result = await db.execute(
        select(ConnectionRequest).where(ConnectionRequest.status == "pending")
    )
    pending_requests = pending_result.scalars().all()

    newly_accepted = 0
    accepted_names: list[str] = []

    for req in pending_requests:
        key = _key_or_none(req.profile_url)
        if not key or key not in contact_id_by_key:
            continue  # not accepted yet — still just a follower we invited
        cas = await db.execute(
            update(ConnectionRequest)
            .where(
                ConnectionRequest.id == req.id,
                ConnectionRequest.status == "pending",
            )
            .values(status="accepted", accepted_at=now)
        )
        if cas.rowcount == 1:
            newly_accepted += 1
            accepted_names.append(req.name)
    await db.commit()

    still_pending = len(pending_requests) - newly_accepted

    # ── Transition 2: bridge accepted → conversation_queued ──
    # Pick up everything currently 'accepted' (the ones just flipped above, plus
    # any straggler from a previous run that crashed before it could queue).
    accepted_result = await db.execute(
        select(ConnectionRequest).where(ConnectionRequest.status == "accepted")
    )
    accepted_requests = accepted_result.scalars().all()

    conversation_queued = 0
    queued_names: list[str] = []
    errors: list[str] = []

    for req in accepted_requests:
        # Guarded CAS: only the run that flips accepted → conversation_queued
        # proceeds to generate + queue. Losers see rowcount 0 and bail.
        cas = await db.execute(
            update(ConnectionRequest)
            .where(
                ConnectionRequest.id == req.id,
                ConnectionRequest.status == "accepted",
            )
            .values(status="conversation_queued")
        )
        if cas.rowcount != 1:
            await db.rollback()  # lost the race — leave the winner to do the work
            continue

        # We won the transition. Generate the message ONLY now.
        key = _key_or_none(req.profile_url)
        contact_id = contact_id_by_key.get(key) if key else None
        if contact_id is None:
            # 'accepted' implies the person is in contacts; if not, this is a
            # real inconsistency. Roll back the flip (stays 'accepted' for a
            # later retry) and surface it loudly instead of guessing.
            await db.rollback()
            msg = f"Accepted request for {req.name} has no matching contact — skipped"
            errors.append(msg)
            logger.error(msg)
            continue

        primary_segment = req.segments[0] if req.segments else None
        use_case = primary_segment or "general"

        try:
            generated = await generate_message(
                db=db,
                contact_id=str(contact_id),
                purpose="introduce",
                segment=primary_segment,
                num_variations=1,
            )
            message = generated["variations"][0] if generated["variations"] else ""

            await add_to_queue(
                db=db,
                contact_id=contact_id,
                use_case=use_case,
                outreach_type="warm",
                purpose="introduce",
                generated_message=message,
            )
            # add_to_queue committed — the status flip + the queue draft land together.
            conversation_queued += 1
            queued_names.append(req.name)
            logger.info(f"Bridge: queued first-touch draft for {req.name}")

        except (ValueError, IntegrityError) as e:
            # A queue item already exists for this contact+purpose (duplicate
            # guard fired). The conversation is effectively already queued, so
            # this is "already done", not a failure. Re-apply the status flip
            # idempotently in a clean transaction and move on.
            await db.rollback()
            await db.execute(
                update(ConnectionRequest)
                .where(
                    ConnectionRequest.id == req.id,
                    ConnectionRequest.status == "accepted",
                )
                .values(status="conversation_queued")
            )
            await db.commit()
            conversation_queued += 1
            queued_names.append(req.name)
            logger.info(f"Bridge: {req.name} already had a queued conversation ({e})")

        except Exception as e:
            # Anything else (e.g. message generation failed): roll back so the
            # request stays 'accepted' and is retried next run. Fail loudly.
            await db.rollback()
            msg = f"Bridge failed for {req.name}: {e}"
            errors.append(msg)
            logger.error(msg)

    logger.info(
        f"Acceptance check: {newly_accepted} newly accepted, "
        f"{still_pending} still pending, "
        f"{conversation_queued} conversations queued, "
        f"{len(errors)} errors"
    )

    return CheckAcceptancesResponse(
        checked=len(pending_requests),
        newly_accepted=newly_accepted,
        still_pending=still_pending,
        accepted_names=accepted_names,
        conversation_queued=conversation_queued,
        queued_names=queued_names,
        errors=errors,
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

    # 'conversation_queued' is a downstream state of 'accepted' — count it as
    # accepted so the bridge doesn't make the acceptance rate appear to drop.
    accepted_states = ("accepted", "conversation_queued")

    total = len(all_requests)
    accepted = sum(1 for r in all_requests if r.status in accepted_states)
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
            if req.status in accepted_states:
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
