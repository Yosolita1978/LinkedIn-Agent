"""
LinkedIn Export Parser

Parses LinkedIn data export CSV files (messages.csv, Connections.csv)
and populates the database.
"""

import csv
import re
import io
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, Message, DataUpload
from app.services.warmth_scorer import update_contact_warmth, is_message_substantive


# Your LinkedIn profile URL - used to determine message direction
YOUR_LINKEDIN_URL = "https://www.linkedin.com/in/crissrodriguez"


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URL for consistent matching."""
    if not url:
        return ""
    # Remove trailing slashes and query params
    url = url.split("?")[0].rstrip("/")
    # Ensure lowercase
    return url.lower()


def parse_connection_date(date_str: str) -> Optional[datetime]:
    """Parse connection date from format '18 Jun 2025'."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y")
    except ValueError:
        return None


def parse_message_date(date_str: str) -> Optional[datetime]:
    """Parse message date from format '2025-06-19 02:27:32 UTC'."""
    if not date_str:
        return None
    try:
        # Remove UTC suffix and parse
        date_str = date_str.replace(" UTC", "").strip()
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def strip_html(content: str) -> str:
    """Remove HTML tags from message content."""
    if not content:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", content)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def is_sponsored_message(from_name: str, content: str) -> bool:
    """Check if message is a sponsored/automated LinkedIn message."""
    if from_name == "LinkedIn Member":
        return True
    if not content:
        return False
    # Check for common sponsored message patterns
    sponsored_patterns = [
        "%FIRSTNAME%",
        "spinmail-quill-editor",
        "Sponsored Conversation",
    ]
    return any(pattern in content for pattern in sponsored_patterns)


async def parse_connections_csv(
    db: AsyncSession,
    file_content: bytes,
    filename: str = "Connections.csv",
) -> dict:
    """
    Parse LinkedIn Connections.csv and create/update contacts.

    Returns dict with processing stats.
    """
    result = {
        "records_processed": 0,
        "contacts_created": 0,
        "contacts_updated": 0,
        "errors": [],
    }

    # Decode file content
    try:
        content = file_content.decode("utf-8")
    except UnicodeDecodeError:
        content = file_content.decode("utf-8-sig")  # Handle BOM

    # LinkedIn exports have notes in first few lines, find the header row
    lines = content.split("\n")
    header_index = 0
    for i, line in enumerate(lines):
        if line.startswith("First Name,"):
            header_index = i
            break

    # Parse CSV starting from header
    csv_content = "\n".join(lines[header_index:])
    reader = csv.DictReader(io.StringIO(csv_content))

    for row in reader:
        try:
            url = row.get("URL", "").strip()
            if not url:
                continue

            normalized_url = normalize_linkedin_url(url)
            first_name = row.get("First Name", "").strip()
            last_name = row.get("Last Name", "").strip()
            name = f"{first_name} {last_name}".strip()

            if not name:
                continue

            # Check if contact exists
            stmt = select(Contact).where(
                Contact.linkedin_url == normalized_url
            )
            existing = await db.execute(stmt)
            contact = existing.scalar_one_or_none()

            connection_date = parse_connection_date(row.get("Connected On", ""))

            if contact:
                # Update existing contact
                contact.company = row.get("Company", "").strip() or contact.company
                contact.position = row.get("Position", "").strip() or contact.position
                contact.email = row.get("Email Address", "").strip() or contact.email
                if connection_date:
                    contact.connection_date = connection_date.date()
                contact.updated_at = datetime.utcnow()
                result["contacts_updated"] += 1
            else:
                # Create new contact
                contact = Contact(
                    linkedin_url=normalized_url,
                    name=name,
                    company=row.get("Company", "").strip() or None,
                    position=row.get("Position", "").strip() or None,
                    email=row.get("Email Address", "").strip() or None,
                    connection_date=connection_date.date() if connection_date else None,
                )
                db.add(contact)
                result["contacts_created"] += 1

            result["records_processed"] += 1

        except Exception as e:
            result["errors"].append(f"Row error: {str(e)}")

    # Record the upload
    upload = DataUpload(
        file_type="connections",
        filename=filename,
        records_processed=result["records_processed"],
    )
    db.add(upload)

    await db.commit()

    return result


async def parse_messages_csv(
    db: AsyncSession,
    file_content: bytes,
    filename: str = "messages.csv",
) -> dict:
    """
    Parse LinkedIn messages.csv and create messages linked to contacts.

    Returns dict with processing stats.
    """
    result = {
        "records_processed": 0,
        "contacts_created": 0,
        "contacts_updated": 0,
        "messages_created": 0,
        "skipped_sponsored": 0,
        "errors": [],
    }

    your_url_normalized = normalize_linkedin_url(YOUR_LINKEDIN_URL)

    # Decode file content
    try:
        content = file_content.decode("utf-8")
    except UnicodeDecodeError:
        content = file_content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))

    # Cache for contacts to avoid repeated DB lookups
    contact_cache: dict[str, Contact] = {}

    for row in reader:
        try:
            from_name = row.get("FROM", "").strip()
            from_url = normalize_linkedin_url(row.get("SENDER PROFILE URL", ""))
            to_name = row.get("TO", "").strip()
            to_url = normalize_linkedin_url(row.get("RECIPIENT PROFILE URLS", ""))
            content_raw = row.get("CONTENT", "")

            # Skip sponsored messages
            if is_sponsored_message(from_name, content_raw):
                result["skipped_sponsored"] += 1
                continue

            # Determine the other person (not you)
            if from_url == your_url_normalized:
                # You sent this message
                direction = "sent"
                other_name = to_name
                other_url = to_url
            elif to_url == your_url_normalized:
                # You received this message
                direction = "received"
                other_name = from_name
                other_url = from_url
            else:
                # Can't determine direction, skip
                result["errors"].append(f"Can't determine direction for message from {from_name} to {to_name}")
                continue

            if not other_url:
                continue

            # Get or create contact
            if other_url in contact_cache:
                contact = contact_cache[other_url]
            else:
                stmt = select(Contact).where(Contact.linkedin_url == other_url)
                existing = await db.execute(stmt)
                contact = existing.scalar_one_or_none()

                if not contact:
                    # Create minimal contact from message data
                    contact = Contact(
                        linkedin_url=other_url,
                        name=other_name or "Unknown",
                    )
                    db.add(contact)
                    await db.flush()  # Get the ID
                    result["contacts_created"] += 1

                contact_cache[other_url] = contact

            # Parse message data
            message_date = parse_message_date(row.get("DATE", ""))
            if not message_date:
                continue

            content_clean = strip_html(content_raw)
            content_length = len(content_clean) if content_clean else 0

            # Create message
            message = Message(
                contact_id=contact.id,
                direction=direction,
                date=message_date,
                subject=row.get("SUBJECT", "").strip() or None,
                content=content_clean or None,
                content_length=content_length,
                conversation_id=row.get("CONVERSATION ID", "").strip() or None,
                is_substantive=is_message_substantive(content_clean),
            )
            db.add(message)
            result["messages_created"] += 1
            result["records_processed"] += 1

        except Exception as e:
            result["errors"].append(f"Row error: {str(e)}")

    # Update contact message stats
    for contact in contact_cache.values():
        await update_contact_message_stats(db, contact)
        result["contacts_updated"] += 1

    # Record the upload
    upload = DataUpload(
        file_type="messages",
        filename=filename,
        records_processed=result["records_processed"],
    )
    db.add(upload)

    await db.commit()

    return result


async def update_contact_message_stats(db: AsyncSession, contact: Contact) -> None:
    """Update a contact's message statistics and warmth score."""
    # Get all messages for this contact
    stmt = select(Message).where(Message.contact_id == contact.id).order_by(Message.date.desc())
    result = await db.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        return

    contact.total_messages = len(messages)
    contact.last_message_date = messages[0].date.date()
    contact.last_message_direction = messages[0].direction
    contact.updated_at = datetime.utcnow()

    # Calculate warmth score
    await update_contact_warmth(db, contact)
