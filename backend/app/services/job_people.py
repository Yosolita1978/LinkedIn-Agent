"""
Job People Service

Turns the people LinkedIn shows on a job page ("People you can reach out to",
"Meet the hiring team") into job_people rows, linked to your contacts when you
already know them.

Called from fetch_job_details(), so it costs no extra page loads.
"""

import re
import uuid
from typing import Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.job_opportunity import JobOpportunity
from app.models.job_person import JobPerson
from app.schemas.jobs import JobDetailOut, JobPersonOut


DEGREE_PATTERN = re.compile(r"[•·]\s*(1st|2nd|3rd\+?)")
PROFILE_SLUG_PATTERN = re.compile(r"/in/([^/?#]+)")
COMPANY_SLUG_PATTERN = re.compile(r"/(company|school|showcase)/([^/?#]+)")
MUTUAL_PATTERN = re.compile(r"mutual connection", re.IGNORECASE)

# Only people she can reach through someone she knows.
COMPANY_PEOPLE_DEGREES = {"1st", "2nd"}
MAX_COMPANY_PEOPLE = 30

# Sources written from the job page itself (replaced together on each fetch).
JOB_PAGE_SOURCES = ["reach_out", "hiring_team", "network_hint"]

# Buttons that can end up inside a person card's text.
PERSON_NOISE_LINES = {"message", "connect", "follow", "show all"}


def parse_person_text(text: str) -> dict:
    """
    Turn a person card into name / degree / headline / reason.

    Typical card text (one item per line):
        Mackenzie Moore Combs
        • 2nd
        Talent @ Crux ⚡️
        School alum from University of Washington
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    name = ""
    degree = None
    rest: list[str] = []

    for line in lines:
        if line.lower() in PERSON_NOISE_LINES:
            continue
        match = DEGREE_PATTERN.search(line)
        if match and degree is None:
            degree = match.group(1)
            before = line[: match.start()].strip()
            if before and not name:
                name = before
            continue
        if not name:
            name = line
        else:
            rest.append(line)

    return {
        "name": name,
        "degree": degree,
        "headline": rest[0] if len(rest) > 0 else None,
        "reason": rest[1] if len(rest) > 1 else None,
    }


async def find_contact_id(db: AsyncSession, profile_url: str) -> Optional[uuid.UUID]:
    """Match a profile URL to a contact by its /in/<slug> part."""
    match = PROFILE_SLUG_PATTERN.search(profile_url or "")
    if not match:
        return None
    slug = match.group(1).lower()
    stored_url = func.lower(Contact.linkedin_url)
    result = await db.execute(
        select(Contact.id)
        .where(or_(stored_url.like(f"%/in/{slug}"), stored_url.like(f"%/in/{slug}/")))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_job_page_people(
    db: AsyncSession,
    job_id: uuid.UUID,
    people: list[dict],
    hints: list[dict],
) -> None:
    """
    Replace this job's job-page people with the latest scrape.
    Doesn't commit; the caller does.
    """
    await db.execute(
        delete(JobPerson).where(
            JobPerson.job_id == job_id, JobPerson.source.in_(JOB_PAGE_SOURCES)
        )
    )

    for person in people:
        parsed = parse_person_text(person["text"])
        if not parsed["name"]:
            continue
        db.add(
            JobPerson(
                job_id=job_id,
                source=person["source"],
                profile_url=person["profile_url"],
                contact_id=await find_contact_id(db, person["profile_url"]),
                **parsed,
            )
        )

    for hint in hints:
        db.add(JobPerson(job_id=job_id, source="network_hint", name=hint["text"][:300]))


def company_people_url(company_url: str) -> Optional[str]:
    """https://www.linkedin.com/company/cruxclimate/life/ → .../company/cruxclimate/people/"""
    match = COMPANY_SLUG_PATTERN.search(company_url or "")
    if not match:
        return None
    return f"https://www.linkedin.com/{match.group(1)}/{match.group(2)}/people/"


async def save_company_people(
    db: AsyncSession,
    job_id: uuid.UUID,
    people: list[dict],
) -> int:
    """
    Replace this job's company_page people with the latest scan (1st/2nd degree only).
    Doesn't commit; the caller does. Returns how many people were saved.
    """
    await db.execute(
        delete(JobPerson).where(JobPerson.job_id == job_id, JobPerson.source == "company_page")
    )

    saved = 0
    for person in people:
        if saved >= MAX_COMPANY_PEOPLE:
            break
        parsed = parse_person_text(person["text"])
        if not parsed["name"] or parsed["degree"] not in COMPANY_PEOPLE_DEGREES:
            continue
        mutual_lines = [
            line.strip()
            for line in person.get("card_text", "").split("\n")
            if MUTUAL_PATTERN.search(line)
        ]
        db.add(
            JobPerson(
                job_id=job_id,
                source="company_page",
                name=parsed["name"],
                degree=parsed["degree"],
                headline=parsed["headline"],
                profile_url=person["profile_url"],
                reason=mutual_lines[0] if mutual_lines else None,
                contact_id=await find_contact_id(db, person["profile_url"]),
            )
        )
        saved += 1
    return saved


async def get_job_people(db: AsyncSession, job_id: uuid.UUID) -> list[JobPerson]:
    result = await db.execute(
        select(JobPerson).where(JobPerson.job_id == job_id).order_by(JobPerson.found_at)
    )
    return list(result.scalars().all())


async def build_job_detail(db: AsyncSession, job: JobOpportunity) -> JobDetailOut:
    """A job with its posting text and the people linked to it."""
    people = await get_job_people(db, job.id)
    return JobDetailOut.model_validate(job).model_copy(
        update={"people": [JobPersonOut.model_validate(person) for person in people]}
    )
