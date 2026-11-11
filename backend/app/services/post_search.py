"""
Hiring Post Search Service

Runs LinkedIn content (posts) searches with Playwright and saves the results to
the hiring_posts table. Jobs attached to posts are also saved to job_opportunities,
so the jobs fit check (POST /api/jobs/details) works on them.

Flow:
1. build_post_search_url() → one LinkedIn posts-search URL per keyword phrase
2. browser.search_posts()  → raw post cards
3. parse_post_card()       → author / headline / posted_ago / attached job
4. upsert                  → new posts inserted, known posts get last_seen_at bumped
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from urllib.parse import quote, urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hiring_post import HiringPost
from app.models.job_opportunity import JobOpportunity
from app.schemas.posts import MAX_POST_TEXT_CHARS, PostOut, PostSearchRequest
from app.services.job_search import start_logged_in_browser
from app.services.linkedin_browser import ScrapingError


logger = logging.getLogger(__name__)

POSTS_SEARCH_BASE_URL = "https://www.linkedin.com/search/results/content/"

DEGREE_PATTERN = re.compile(r"•\s*(1st|2nd|3rd\+?)")
POSTED_AGO_PATTERN = re.compile(r"^(\d+\s?(?:s|m|h|d|w|mo|yr))\b")
JOB_ID_PATTERN = re.compile(r"/jobs/view/(\d+)")

# Lines inside the post text that are buttons, not content.
POST_TEXT_NOISE_LINES = {"… more", "…more", "... more", "see less", "…see less", "… see less"}

# Button lines in the card header (between the name and the post) that aren't a headline.
HEADER_NOISE_LINES = {
    "follow", "join", "connect", "message", "promoted", "premium",
    "view my services", "visit my website", "view my newsletter", "view my portfolio",
    "book an appointment", "view my blog", "view my course",
}


def build_post_search_url(keywords: str, date_posted: str) -> str:
    params = {
        "keywords": keywords,
        "origin": "FACETED_SEARCH",
        "datePosted": json.dumps([date_posted]),  # LinkedIn expects ["past-24h"]
    }
    return f"{POSTS_SEARCH_BASE_URL}?{urlencode(params, quote_via=quote)}"


def make_fingerprint(author: str, post_text: str) -> str:
    normalized_text = " ".join(post_text.lower().split())[:300]
    return hashlib.sha1(f"{author}|{normalized_text}".encode("utf-8")).hexdigest()


def clean_post_text(text: str) -> str:
    lines = [line.rstrip() for line in text.split("\n")]
    kept = [line for line in lines if line.strip().lower() not in POST_TEXT_NOISE_LINES]
    return "\n".join(kept).strip()


def parse_post_card(raw: dict) -> dict:
    """
    Turn a raw post card into author / headline / posted_ago / attached job.

    Typical card text (one item per line):
        Feed post
        Shir Sadeh
        • 3rd+
        Talent Acquisition Partner | at Reco
        15h
        Follow
        <post text>
        FDE / Reco / Tel Aviv-Yafo (On-site) / View job     ← attached job, if any

    Group posts put the group name first: "<Group>", "Neelima M • 3rd+", "12h", "Join".
    Company page posts have no degree: "<Company>", "12,345 followers", "1d", "Follow".
    """
    lines = [line.strip() for line in raw["card_text"].split("\n") if line.strip()]
    lines = [line for line in lines if line != "Feed post"]

    author_name = ""
    author_degree = None
    group_name = None
    degree_index = None

    for index, line in enumerate(lines):
        match = DEGREE_PATTERN.search(line)
        if match:
            degree_index = index
            author_degree = match.group(1)
            name_part = line[: match.start()].strip()
            if name_part:
                author_name = name_part
                if index > 0:
                    group_name = lines[index - 1]  # "<Group>" then "Name • 3rd+"
            elif index > 0:
                author_name = lines[index - 1]     # "Name" then "• 3rd+"
            break

    # No degree line: a company or school page post. Its name is the first line.
    header_start = degree_index
    if degree_index is None and lines:
        author_name = lines[0]
        header_start = 0

    # The author link text ("Shir Sadeh • 3rd+") is the most reliable name source.
    link_text = raw.get("author_link_text", "")
    if link_text:
        author_name = DEGREE_PATTERN.split(link_text)[0].strip() or author_name

    author_headline = None
    posted_ago = None
    if header_start is not None:
        for line in lines[header_start + 1 : header_start + 7]:
            ago = POSTED_AGO_PATTERN.match(line)
            if ago:
                posted_ago = ago.group(1)
                break
            if line.lower() in HEADER_NOISE_LINES or line == author_name:
                continue
            if author_headline is None:
                author_headline = line

    # Attached job card: "<title>", "<company>", "<location>", "View job"
    job = None
    job_match = JOB_ID_PATTERN.search(raw.get("job_url", ""))
    if job_match:
        job = {"linkedin_job_id": job_match.group(1), "title": "", "company": None, "location": None}
        if "View job" in lines:
            view_index = lines.index("View job")
            if view_index >= 3:
                job["title"] = lines[view_index - 3]
                job["company"] = lines[view_index - 2]
                job["location"] = lines[view_index - 1]

    post_text = clean_post_text(raw.get("post_text", "")) or "\n".join(lines)

    return {
        "author_name": author_name,
        "author_degree": author_degree,
        "author_headline": author_headline,
        "author_url": raw.get("author_url") or None,
        "group_name": group_name,
        "post_text": post_text[:MAX_POST_TEXT_CHARS],
        "posted_ago": posted_ago,
        "job": job,
    }


async def search_and_save_posts(db: AsyncSession, request: PostSearchRequest) -> dict:
    """
    Run one LinkedIn posts search per keyword and save the results.

    Raises ValueError if the LinkedIn session is not logged in.
    Returns a dict matching PostSearchResponse.
    """
    found_by_fingerprint: dict[str, dict] = {}
    jobs_by_id: dict[str, dict] = {}
    errors: list[str] = []

    browser = await start_logged_in_browser()
    try:
        for keywords in request.keywords:
            search_url = build_post_search_url(keywords, request.date_posted)
            try:
                raw_posts = await browser.search_posts(search_url, max_items=request.max_per_keyword)
            except ScrapingError as e:
                logger.warning(f"Posts search failed for '{keywords}': {e}")
                errors.append(f"{keywords}: {e}")
                continue

            for raw in raw_posts:
                parsed = parse_post_card(raw)
                author_key = parsed["author_url"] or parsed["author_name"]
                fingerprint = make_fingerprint(author_key, parsed["post_text"])
                if fingerprint in found_by_fingerprint:
                    continue  # already found by an earlier keyword

                job = parsed.pop("job")
                job_url = None
                if job:
                    job_url = f"https://www.linkedin.com/jobs/view/{job['linkedin_job_id']}/"
                    if job["linkedin_job_id"] not in jobs_by_id:
                        jobs_by_id[job["linkedin_job_id"]] = {**job, "search_keywords": f"post: {keywords}"}

                found_by_fingerprint[fingerprint] = {
                    **parsed,
                    "fingerprint": fingerprint,
                    "job_url": job_url,
                    "search_keywords": keywords,
                }
    finally:
        await browser.stop()

    # Upsert posts: insert new ones, bump last_seen_at on known ones (keep status/notes)
    existing_result = await db.execute(
        select(HiringPost).where(HiringPost.fingerprint.in_(list(found_by_fingerprint.keys())))
    )
    existing_by_fingerprint = {post.fingerprint: post for post in existing_result.scalars().all()}

    now = datetime.utcnow()
    saved_posts: list[HiringPost] = []
    new_count = 0

    for fingerprint, data in found_by_fingerprint.items():
        post = existing_by_fingerprint.get(fingerprint)
        if post is not None:
            post.last_seen_at = now
        else:
            post = HiringPost(**data, first_seen_at=now, last_seen_at=now)
            db.add(post)
            new_count += 1
        saved_posts.append(post)

    # Save attached jobs that aren't in job_opportunities yet (never overwrite known ones)
    new_jobs_count = 0
    if jobs_by_id:
        known_jobs_result = await db.execute(
            select(JobOpportunity.linkedin_job_id).where(
                JobOpportunity.linkedin_job_id.in_(list(jobs_by_id.keys()))
            )
        )
        known_job_ids = set(known_jobs_result.scalars().all())
        for job_id, job in jobs_by_id.items():
            if job_id in known_job_ids:
                continue
            db.add(
                JobOpportunity(
                    linkedin_job_id=job_id,
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    job_url=f"https://www.linkedin.com/jobs/view/{job_id}/",
                    search_keywords=job["search_keywords"],
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
            new_jobs_count += 1

    await db.commit()

    logger.info(
        f"Posts search done: {new_count} new, {len(existing_by_fingerprint)} already saved, "
        f"{new_jobs_count} new jobs"
    )
    return {
        "posts": [PostOut.model_validate(post) for post in saved_posts],
        "new_count": new_count,
        "already_saved_count": len(existing_by_fingerprint),
        "new_jobs_count": new_jobs_count,
        "errors": errors,
    }
