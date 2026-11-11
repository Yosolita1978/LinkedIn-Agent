"""
Job Search Service

Runs LinkedIn Jobs searches with Playwright and saves the results to
the job_opportunities table (deduped by LinkedIn job id).

Flow:
1. build_search_url()     → one LinkedIn Jobs URL per keyword phrase
2. browser.search_jobs()  → raw cards (job id + card text)
3. parse_job_card()       → title / company / location
4. upsert                 → new jobs inserted, known jobs get last_seen_at bumped

fetch_job_details() is separate: it opens individual job pages (only for jobs
worth a closer look) and saves the full posting text.
"""

import logging
import uuid
from datetime import datetime
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_opportunity import JobOpportunity
from app.schemas.jobs import (
    MAX_DESCRIPTION_CHARS,
    JobDetailsRequest,
    JobOut,
    JobSearchRequest,
)
from app.services.job_people import (
    build_job_detail,
    company_people_url,
    save_company_people,
    save_job_page_people,
)
from app.services.linkedin_browser import LinkedInBrowser, ScrapingError


logger = logging.getLogger(__name__)

JOBS_SEARCH_BASE_URL = "https://www.linkedin.com/jobs/search/"

# Card lines that are badges, not company or location.
CARD_NOISE_LINES = {
    "promoted",
    "viewed",
    "applied",
    "saved",
    "easy apply",
    "actively reviewing applicants",
    "be an early applicant",
    "dismiss",
}


def build_search_url(
    keywords: str,
    location: str,
    remote_only: bool,
    posted_within_days: int | None,
) -> str:
    params = {"keywords": keywords, "location": location}
    if remote_only:
        params["f_WT"] = "2"  # LinkedIn's "Remote" workplace filter
    if posted_within_days:
        params["f_TPR"] = f"r{posted_within_days * 86400}"  # posted within N seconds
    return f"{JOBS_SEARCH_BASE_URL}?{urlencode(params)}"


def clean_title(text: str) -> str:
    first_line = text.split("\n")[0].strip()
    return first_line.removesuffix(" with verification").strip()


def parse_job_card(title_text: str, card_text: str) -> dict:
    """
    Turn a raw job card into title / company / location.

    Typical card text (one item per line):
        Senior AI Engineer
        Senior AI Engineer with verification
        Acme AI
        Seattle, WA (Remote)
        $150K/yr - $190K/yr
        Promoted · Easy Apply
    """
    lines = [line.strip() for line in card_text.split("\n") if line.strip()]
    title = clean_title(title_text) or (clean_title(lines[0]) if lines else "")

    remaining = []
    for line in lines:
        if title and title in line:
            continue  # the title, its "with verification" copy, or "Selected, <title>"
        if line.lower() in CARD_NOISE_LINES:
            continue
        remaining.append(line)

    return {
        "title": title,
        "company": remaining[0] if len(remaining) > 0 else None,
        "location": remaining[1] if len(remaining) > 1 else None,
    }


async def start_logged_in_browser() -> LinkedInBrowser:
    """
    Start a visible browser (LinkedIn blocks headless Chromium) and check login.
    Raises ValueError if not logged in. Caller must call browser.stop().
    """
    browser = LinkedInBrowser()
    await browser.start(headless=False)
    if not await browser.is_logged_in():
        await browser.stop()
        raise ValueError(
            "LinkedIn session not authenticated. "
            "Run the manual login script first: uv run python test_auth.py"
        )
    return browser


async def search_and_save_jobs(db: AsyncSession, request: JobSearchRequest) -> dict:
    """
    Run one LinkedIn Jobs search per keyword and save the results.

    Raises ValueError if the LinkedIn session is not logged in.
    Returns a dict matching JobSearchResponse.
    """
    found_by_id: dict[str, dict] = {}
    errors: list[str] = []

    browser = await start_logged_in_browser()
    try:
        for keywords in request.keywords:
            search_url = build_search_url(
                keywords, request.location, request.remote_only, request.posted_within_days
            )
            try:
                raw_jobs = await browser.search_jobs(search_url, max_items=request.max_per_keyword)
            except ScrapingError as e:
                logger.warning(f"Jobs search failed for '{keywords}': {e}")
                errors.append(f"{keywords}: {e}")
                continue

            for raw in raw_jobs:
                job_id = raw["linkedin_job_id"]
                if job_id in found_by_id:
                    continue  # already found by an earlier keyword
                parsed = parse_job_card(raw["title_text"], raw["card_text"])
                found_by_id[job_id] = {
                    **parsed,
                    "linkedin_job_id": job_id,
                    "job_url": f"https://www.linkedin.com/jobs/view/{job_id}/",
                    "card_text": raw["card_text"],
                    "search_keywords": keywords,
                }
    finally:
        await browser.stop()

    # Upsert: insert new jobs, bump last_seen_at on known ones (keep status/notes)
    existing_result = await db.execute(
        select(JobOpportunity).where(
            JobOpportunity.linkedin_job_id.in_(list(found_by_id.keys()))
        )
    )
    existing_by_id = {job.linkedin_job_id: job for job in existing_result.scalars().all()}

    now = datetime.utcnow()
    saved_jobs: list[JobOpportunity] = []
    new_count = 0

    for job_id, data in found_by_id.items():
        job = existing_by_id.get(job_id)
        if job is not None:
            job.last_seen_at = now
            # Fill fields an earlier (broken) scrape left empty; never overwrite.
            if not job.company and data["company"]:
                job.company = data["company"]
                job.location = data["location"]
                job.card_text = data["card_text"]
        else:
            job = JobOpportunity(**data, first_seen_at=now, last_seen_at=now)
            db.add(job)
            new_count += 1
        saved_jobs.append(job)

    await db.commit()

    logger.info(f"Jobs search done: {new_count} new, {len(existing_by_id)} already saved")
    return {
        "jobs": [JobOut.model_validate(job) for job in saved_jobs],
        "new_count": new_count,
        "already_saved_count": len(existing_by_id),
        "errors": errors,
    }


async def apply_job_details(db: AsyncSession, job: JobOpportunity, details: dict) -> None:
    """Save what scrape_job_details() returned onto the job. Doesn't commit."""
    # Put the top-card line (location, pay, Remote/Full-time) above the
    # description so the fit check sees it.
    full_text = details["description"]
    if details["top_card"]:
        full_text = f"{details['top_card']}\n\n{full_text}"
    job.description = full_text[:MAX_DESCRIPTION_CHARS]
    job.details_fetched_at = datetime.utcnow()
    if not job.company and details["company"]:
        job.company = details["company"]
    await save_job_page_people(db, job.id, details["people"], details["people_hints"])


async def fetch_job_details(db: AsyncSession, request: JobDetailsRequest) -> dict:
    """
    Save the full posting text for up to 10 saved jobs.

    Jobs that already have a description are skipped unless refresh=True,
    so the browser only opens when there is something to fetch.
    Raises ValueError if the LinkedIn session is not logged in.
    Returns a dict matching JobDetailsResponse.
    """
    errors: list[str] = []
    closed_job_ids: list[uuid.UUID] = []
    fetched_count = 0

    result = await db.execute(
        select(JobOpportunity).where(JobOpportunity.id.in_(request.job_ids))
    )
    jobs_by_id = {job.id: job for job in result.scalars().all()}

    for job_id in request.job_ids:
        if job_id not in jobs_by_id:
            errors.append(f"{job_id}: job not found")

    jobs = [jobs_by_id[job_id] for job_id in request.job_ids if job_id in jobs_by_id]
    to_fetch = [job for job in jobs if request.refresh or not job.description]

    if to_fetch:
        browser = await start_logged_in_browser()
        try:
            for job in to_fetch:
                try:
                    details = await browser.scrape_job_details(job.job_url)
                except ScrapingError as e:
                    logger.warning(f"Job details failed for {job.job_url}: {e}")
                    errors.append(f"{job.title} @ {job.company}: {e}")
                    continue

                await apply_job_details(db, job, details)
                fetched_count += 1
                if details["is_closed"]:
                    closed_job_ids.append(job.id)
        finally:
            await browser.stop()

        await db.commit()

    logger.info(f"Job details: {fetched_count} fetched, {len(errors)} errors")
    return {
        "jobs": [await build_job_detail(db, job) for job in jobs],
        "fetched_count": fetched_count,
        "closed_job_ids": closed_job_ids,
        "errors": errors,
    }


async def scan_job_people(db: AsyncSession, job_id: uuid.UUID) -> dict:
    """
    Find who she can reach at a saved job's company. Two page loads:
    1. the job page (refreshes the posting, "People you can reach out to", company link)
    2. the company's People page (1st/2nd-degree connections, with mutual-connection lines)

    Raises LookupError if the job doesn't exist, ValueError if not logged in,
    ScrapingError if the job page can't be read.
    Returns a dict matching JobPeopleScanResponse.
    """
    job = await db.get(JobOpportunity, job_id)
    if job is None:
        raise LookupError("Job not found")

    errors: list[str] = []
    people_url = None
    company_people_count = 0

    browser = await start_logged_in_browser()
    try:
        details = await browser.scrape_job_details(job.job_url)
        await apply_job_details(db, job, details)

        people_url = company_people_url(details["company_url"])
        if people_url is None:
            errors.append("No company page link on the job page")
        else:
            try:
                company_people = await browser.search_company_people(people_url)
                company_people_count = await save_company_people(db, job.id, company_people)
            except ScrapingError as e:
                logger.warning(f"Company people failed for {people_url}: {e}")
                errors.append(f"Company people: {e}")
    finally:
        await browser.stop()

    await db.commit()

    logger.info(f"People scan for {job.company}: {company_people_count} 1st/2nd-degree people")
    return {
        "job": await build_job_detail(db, job),
        "company_people_url": people_url,
        "company_people_count": company_people_count,
        "errors": errors,
    }
