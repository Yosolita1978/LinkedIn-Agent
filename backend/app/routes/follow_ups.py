"""
Follow-up routes — keep every conversation moving.

Each follow-up is one person + one opportunity, with a stage, what happened last,
and the next action with a due date.

Flow:
1. POST  /api/follow-ups            → start tracking someone
2. GET   /api/follow-ups?due=today  → what's due (overdue + today first)
3. POST  /api/follow-ups/{id}/touch → log what happened + set the next step
4. PATCH /api/follow-ups/{id}       → fix fields or close the thread
"""

from datetime import date, datetime, timedelta
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.follow_up import FollowUp
from app.schemas.follow_ups import (
    VALID_STAGES,
    VALID_STATUSES,
    FollowUpCreate,
    FollowUpListResponse,
    FollowUpOut,
    FollowUpTouch,
    FollowUpUpdate,
)
from app.services.job_people import find_contact_id


router = APIRouter(prefix="/api/follow-ups", tags=["follow-ups"])


def check_stage(stage: str) -> None:
    if stage not in VALID_STAGES:
        raise HTTPException(
            status_code=400, detail=f"Invalid stage. Options: {', '.join(VALID_STAGES)}"
        )


def check_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Options: {', '.join(VALID_STATUSES)}"
        )


def history_entry(summary: str, stage: Optional[str]) -> dict[str, Optional[str]]:
    return {"at": datetime.utcnow().isoformat(), "summary": summary, "stage": stage}


def set_stage(follow_up: FollowUp, stage: str) -> None:
    check_stage(stage)
    follow_up.stage = stage
    if stage == "closed":
        follow_up.status = "done"


async def get_follow_up_or_404(db: AsyncSession, follow_up_id: UUID) -> FollowUp:
    follow_up = await db.get(FollowUp, follow_up_id)
    if follow_up is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return follow_up


@router.post("", response_model=FollowUpOut, status_code=201)
async def create_follow_up(request: FollowUpCreate, db: AsyncSession = Depends(get_db)):
    """Start tracking a person. Returns 409 if an open follow-up already exists for them."""
    check_stage(request.stage)

    # One open thread per person (by profile URL, or by name + company without one).
    if request.profile_url:
        normalized = request.profile_url.split("?")[0].rstrip("/").lower()
        duplicate_filter = func.rtrim(func.lower(FollowUp.profile_url), "/") == normalized
    else:
        duplicate_filter = and_(
            func.lower(FollowUp.name) == request.name.lower(),
            func.lower(func.coalesce(FollowUp.company, "")) == (request.company or "").lower(),
        )
    existing = await db.execute(
        select(FollowUp.id).where(FollowUp.status == "open", duplicate_filter).limit(1)
    )
    existing_id = existing.scalar_one_or_none()
    if existing_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"An open follow-up already exists for this person: {existing_id}. "
            "Log a touch on it instead.",
        )

    follow_up = FollowUp(
        name=request.name,
        profile_url=request.profile_url,
        company=request.company,
        job_id=request.job_id,
        post_id=request.post_id,
        stage=request.stage,
        next_action=request.next_action,
        due_date=request.due_date,
        notes=request.notes,
        contact_id=await find_contact_id(db, request.profile_url or ""),
        history=[],
    )
    if request.last_touch:
        follow_up.last_touch = request.last_touch
        follow_up.last_touch_at = datetime.utcnow()
        follow_up.history = [history_entry(request.last_touch, request.stage)]
    if request.stage == "closed":
        follow_up.status = "done"

    db.add(follow_up)
    await db.commit()
    await db.refresh(follow_up)
    return follow_up


@router.get("", response_model=FollowUpListResponse)
async def list_follow_ups(
    due: Optional[Literal["overdue", "today", "week"]] = Query(
        None, description="overdue = before today; today = today or earlier; week = next 7 days or earlier"
    ),
    status: str = Query("open", description="open, done, or all"),
    stage: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Match name or company"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List follow-ups, soonest due first (no due date last)."""
    today = date.today()

    stmt = select(FollowUp)
    if status != "all":
        check_status(status)
        stmt = stmt.where(FollowUp.status == status)
    if stage:
        check_stage(stage)
        stmt = stmt.where(FollowUp.stage == stage)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(FollowUp.name.ilike(pattern), FollowUp.company.ilike(pattern)))
    if due == "overdue":
        stmt = stmt.where(FollowUp.due_date < today)
    elif due == "today":
        stmt = stmt.where(FollowUp.due_date <= today)
    elif due == "week":
        stmt = stmt.where(FollowUp.due_date <= today + timedelta(days=7))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    rows_result = await db.execute(
        stmt.order_by(FollowUp.due_date.asc().nulls_last(), FollowUp.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    follow_ups = rows_result.scalars().all()

    open_rows = select(FollowUp).where(FollowUp.status == "open")
    overdue_result = await db.execute(
        select(func.count()).select_from(open_rows.where(FollowUp.due_date < today).subquery())
    )
    due_today_result = await db.execute(
        select(func.count()).select_from(open_rows.where(FollowUp.due_date == today).subquery())
    )
    stage_result = await db.execute(
        select(FollowUp.stage, func.count())
        .where(FollowUp.status == "open")
        .group_by(FollowUp.stage)
    )

    return FollowUpListResponse(
        follow_ups=[FollowUpOut.model_validate(row) for row in follow_ups],
        total=total,
        overdue_count=overdue_result.scalar() or 0,
        due_today_count=due_today_result.scalar() or 0,
        stage_counts={row[0]: row[1] for row in stage_result.all()},
    )


@router.get("/{follow_up_id}", response_model=FollowUpOut)
async def get_follow_up(follow_up_id: UUID, db: AsyncSession = Depends(get_db)):
    """One follow-up with its full history."""
    return await get_follow_up_or_404(db, follow_up_id)


@router.post("/{follow_up_id}/touch", response_model=FollowUpOut)
async def log_touch(
    follow_up_id: UUID,
    request: FollowUpTouch,
    db: AsyncSession = Depends(get_db),
):
    """
    Log what happened and set the next step.
    next_action and due_date replace the current ones (omit = nothing scheduled).
    """
    follow_up = await get_follow_up_or_404(db, follow_up_id)

    if request.stage is not None:
        set_stage(follow_up, request.stage)

    follow_up.last_touch = request.summary
    follow_up.last_touch_at = datetime.utcnow()
    follow_up.next_action = request.next_action
    follow_up.due_date = request.due_date
    # Assign a new list so SQLAlchemy notices the JSONB change.
    follow_up.history = [*follow_up.history, history_entry(request.summary, follow_up.stage)]

    await db.commit()
    await db.refresh(follow_up)
    return follow_up


@router.patch("/{follow_up_id}", response_model=FollowUpOut)
async def update_follow_up(
    follow_up_id: UUID,
    request: FollowUpUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Fix fields or close the thread. Only the fields you send change."""
    follow_up = await get_follow_up_or_404(db, follow_up_id)
    changes = request.model_dump(exclude_unset=True)

    # These columns are required; null means "leave as is".
    for required_field in ("name", "stage", "status"):
        if changes.get(required_field, "") is None:
            changes.pop(required_field)

    if "status" in changes:
        check_status(changes["status"])
    if "stage" in changes:
        set_stage(follow_up, changes.pop("stage"))  # may also set status to done

    for field, value in changes.items():
        setattr(follow_up, field, value)

    if "profile_url" in changes:
        follow_up.contact_id = await find_contact_id(db, follow_up.profile_url or "")

    await db.commit()
    await db.refresh(follow_up)
    return follow_up
