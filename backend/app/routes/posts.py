"""
Hiring post routes — search LinkedIn posts where people say they're hiring.

Flow:
1. POST  /api/posts/search → run LinkedIn posts searches (browser, slow) and save results
2. GET   /api/posts        → list saved posts (filter by status, search text)
3. GET   /api/posts/{id}   → one post
4. PATCH /api/posts/{id}   → mark a post interested / contacted / skipped, add notes
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.hiring_post import HiringPost
from app.schemas.posts import (
    VALID_POST_STATUSES,
    PostSearchRequest,
    PostSearchResponse,
    PostListResponse,
    PostOut,
    PostUpdate,
)
from app.services.post_search import search_and_save_posts
from app.services.linkedin_browser import ScrapingError


router = APIRouter(prefix="/api/posts", tags=["posts"])


def check_status(status: str) -> None:
    if status not in VALID_POST_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Options: {', '.join(VALID_POST_STATUSES)}",
        )


@router.post("/search", response_model=PostSearchResponse)
async def search_posts_route(
    request: PostSearchRequest = PostSearchRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Search LinkedIn posts (one search per keyword phrase) and save the results.

    Opens a visible browser — takes roughly 20-40 seconds per keyword.
    """
    if not request.keywords:
        raise HTTPException(status_code=400, detail="Provide at least one keyword phrase")

    try:
        return await search_and_save_posts(db, request)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ScrapingError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("", response_model=PostListResponse)
async def list_posts(
    status: Optional[str] = Query(None, description="Filter: new, interested, contacted, skipped"),
    search: Optional[str] = Query(None, description="Match author, headline or post text"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List saved posts, newest first."""
    if status:
        check_status(status)

    stmt = select(HiringPost)
    if status:
        stmt = stmt.where(HiringPost.status == status)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                HiringPost.author_name.ilike(pattern),
                HiringPost.author_headline.ilike(pattern),
                HiringPost.post_text.ilike(pattern),
            )
        )

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    posts_result = await db.execute(
        stmt.order_by(HiringPost.first_seen_at.desc()).limit(limit).offset(offset)
    )
    posts = posts_result.scalars().all()

    counts_result = await db.execute(
        select(HiringPost.status, func.count()).group_by(HiringPost.status)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    return PostListResponse(
        posts=[PostOut.model_validate(post) for post in posts],
        total=total,
        counts=counts,
    )


@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: UUID, db: AsyncSession = Depends(get_db)):
    """One saved post."""
    post = await db.get(HiringPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/{post_id}", response_model=PostOut)
async def update_post(
    post_id: UUID,
    request: PostUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a post's status and/or notes."""
    post = await db.get(HiringPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    if request.status is not None:
        check_status(request.status)
        post.status = request.status
    if request.notes is not None:
        post.notes = request.notes

    await db.commit()
    await db.refresh(post)
    return post
