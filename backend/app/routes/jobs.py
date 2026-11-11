"""
Job routes — search LinkedIn Jobs and track the postings you care about.

Flow:
1. POST  /api/jobs/search  → run LinkedIn Jobs searches (browser, slow) and save results
2. GET   /api/jobs         → list saved jobs (filter by status, search text)
3. POST  /api/jobs/details → open up to 10 job pages (browser) and save the full posting text
4. GET   /api/jobs/{id}    → one job, including the saved posting text
5. PATCH /api/jobs/{id}    → mark a job interested / applied / skipped, add notes
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job_opportunity import JobOpportunity
from app.schemas.jobs import (
    VALID_JOB_STATUSES,
    JobSearchRequest,
    JobSearchResponse,
    JobListResponse,
    JobOut,
    JobDetailOut,
    JobDetailsRequest,
    JobDetailsResponse,
    JobPeopleScanResponse,
    JobUpdate,
)
from app.services.job_people import build_job_detail
from app.services.job_search import search_and_save_jobs, fetch_job_details, scan_job_people
from app.services.linkedin_browser import ScrapingError


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs_route(
    request: JobSearchRequest = JobSearchRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Search LinkedIn Jobs (one search per keyword phrase) and save the results.

    Opens a visible browser — takes roughly 15-30 seconds per keyword.
    """
    if not request.keywords:
        raise HTTPException(status_code=400, detail="Provide at least one keyword phrase")

    try:
        return await search_and_save_jobs(db, request)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ScrapingError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter: new, interested, applied, skipped"),
    search: Optional[str] = Query(None, description="Match title or company"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List saved jobs, newest first."""
    if status and status not in VALID_JOB_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Options: {', '.join(VALID_JOB_STATUSES)}",
        )

    stmt = select(JobOpportunity)
    if status:
        stmt = stmt.where(JobOpportunity.status == status)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(JobOpportunity.title.ilike(pattern), JobOpportunity.company.ilike(pattern))
        )

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    jobs_result = await db.execute(
        stmt.order_by(JobOpportunity.first_seen_at.desc()).limit(limit).offset(offset)
    )
    jobs = jobs_result.scalars().all()

    counts_result = await db.execute(
        select(JobOpportunity.status, func.count()).group_by(JobOpportunity.status)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    return JobListResponse(
        jobs=[JobOut.model_validate(job) for job in jobs],
        total=total,
        counts=counts,
    )


@router.post("/details", response_model=JobDetailsResponse)
async def fetch_job_details_route(
    request: JobDetailsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Save the full posting text for up to 10 saved jobs.

    Opens a visible browser only for jobs without saved text (or all, with refresh=true).
    Takes roughly 5-10 seconds per job.
    """
    try:
        return await fetch_job_details(db, request)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/{job_id}/people/scan", response_model=JobPeopleScanResponse)
async def scan_job_people_route(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Find who you can reach at this job's company: refreshes the job page
    ("People you can reach out to") and reads the company's People page for
    1st/2nd-degree connections.

    Opens a visible browser — takes roughly 20-30 seconds.
    """
    try:
        return await scan_job_people(db, job_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ScrapingError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{job_id}", response_model=JobDetailOut)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """One saved job, with its full posting text and linked people once details are fetched."""
    job = await db.get(JobOpportunity, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return await build_job_detail(db, job)


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: UUID,
    request: JobUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a job's status and/or notes."""
    job = await db.get(JobOpportunity, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.status is not None:
        if request.status not in VALID_JOB_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Options: {', '.join(VALID_JOB_STATUSES)}",
            )
        job.status = request.status
    if request.notes is not None:
        job.notes = request.notes

    await db.commit()
    await db.refresh(job)
    return job
