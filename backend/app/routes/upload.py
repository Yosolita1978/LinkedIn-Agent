"""
Upload routes for LinkedIn data exports.
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Contact, Message, DataUpload
from app.schemas.upload import DataUploadResponse, UploadResult, UploadStatusResponse
from app.services.export_parser import parse_connections_csv, parse_messages_csv

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/connections", response_model=UploadResult)
async def upload_connections(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload LinkedIn Connections.csv file.

    Creates or updates contacts based on the export data.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    result = await parse_connections_csv(db, content, file.filename)

    return UploadResult(
        records_processed=result["records_processed"],
        contacts_created=result["contacts_created"],
        contacts_updated=result["contacts_updated"],
        errors=result["errors"],
    )


@router.post("/messages", response_model=UploadResult)
async def upload_messages(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload LinkedIn messages.csv file.

    Creates messages and links them to contacts.
    Also triggers warmth score recalculation (when implemented).
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    result = await parse_messages_csv(db, content, file.filename)

    return UploadResult(
        records_processed=result["records_processed"],
        contacts_created=result["contacts_created"],
        contacts_updated=result["contacts_updated"],
        messages_created=result["messages_created"],
        errors=result["errors"],
    )


@router.get("/status", response_model=UploadStatusResponse)
async def get_upload_status(db: AsyncSession = Depends(get_db)):
    """
    Get the status of data uploads.

    Returns timestamps of last uploads and record counts.
    """
    # Get last messages upload
    stmt = (
        select(DataUpload)
        .where(DataUpload.file_type == "messages")
        .order_by(DataUpload.uploaded_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_messages = result.scalar_one_or_none()

    # Get last connections upload
    stmt = (
        select(DataUpload)
        .where(DataUpload.file_type == "connections")
        .order_by(DataUpload.uploaded_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_connections = result.scalar_one_or_none()

    # Get total counts
    contacts_count = await db.execute(select(func.count(Contact.id)))
    total_contacts = contacts_count.scalar() or 0

    messages_count = await db.execute(select(func.count(Message.id)))
    total_messages = messages_count.scalar() or 0

    return UploadStatusResponse(
        last_messages_upload=last_messages.uploaded_at if last_messages else None,
        last_connections_upload=last_connections.uploaded_at if last_connections else None,
        total_contacts=total_contacts,
        total_messages=total_messages,
    )
