"""
Message Generation routes - generate personalized outreach messages.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.message_generator import generate_message, generate_batch_messages


router = APIRouter(prefix="/api/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    contact_id: str
    purpose: str = Field(
        default="reconnect",
        description="Type: reconnect, introduce, follow_up, invite_community, ask_advice, congratulate, share_resource",
    )
    segment: Optional[str] = Field(
        default=None,
        description="Override segment: mujertech, cascadia, job_target",
    )
    custom_context: Optional[str] = Field(
        default=None,
        description="Additional context for the message",
    )
    num_variations: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Number of message variations to generate",
    )


class BatchGenerateRequest(BaseModel):
    contact_ids: list[str]
    purpose: str = "reconnect"
    segment: Optional[str] = None


@router.post("/message")
async def generate_outreach_message(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate personalized outreach message(s) for a contact.

    Uses Claude to create messages based on:
    - Contact profile and history
    - Segment context (MujerTech, Cascadia, Job Search)
    - Resurrection hooks (if any)
    - Specified purpose

    Returns multiple variations to choose from.
    """
    valid_purposes = [
        "reconnect", "introduce", "follow_up", "invite_community",
        "ask_advice", "congratulate", "share_resource"
    ]

    if request.purpose not in valid_purposes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose. Options: {', '.join(valid_purposes)}",
        )

    valid_segments = ["mujertech", "cascadia", "job_target"]
    if request.segment and request.segment not in valid_segments:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid segment. Options: {', '.join(valid_segments)}",
        )

    try:
        result = await generate_message(
            db=db,
            contact_id=request.contact_id,
            purpose=request.purpose,
            segment=request.segment,
            custom_context=request.custom_context,
            num_variations=request.num_variations,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/batch")
async def generate_batch_outreach_messages(
    request: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate messages for multiple contacts at once.

    Useful for campaign-style outreach.
    Limited to 10 contacts per batch to manage API costs.
    """
    if len(request.contact_ids) > 10:
        raise HTTPException(
            status_code=400,
            detail="Batch limited to 10 contacts. Split into multiple requests.",
        )

    results = await generate_batch_messages(
        db=db,
        contact_ids=request.contact_ids,
        purpose=request.purpose,
        segment=request.segment,
    )

    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    return {
        "total": len(request.contact_ids),
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
    }


@router.get("/purposes")
async def list_purposes():
    """
    List available message purposes with descriptions.
    """
    return {
        "purposes": [
            {"id": "reconnect", "description": "Reconnect after period of no communication"},
            {"id": "introduce", "description": "Make a first meaningful connection"},
            {"id": "follow_up", "description": "Follow up on previous conversation"},
            {"id": "invite_community", "description": "Invite to community or event"},
            {"id": "ask_advice", "description": "Ask for perspective or advice"},
            {"id": "congratulate", "description": "Congratulate on achievement"},
            {"id": "share_resource", "description": "Share something valuable"},
        ]
    }