"""
App settings routes — user-configurable dashboard + persona settings.

The settings table is a singleton (one row). GET creates a default row if the
table is empty, so the frontend always gets a valid object back.

Persona fields fall back to the matching PERSONA_* value in .env whenever the
stored value is empty, so the UI can override config without a restart while a
fresh (unedited) row behaves exactly like the env-only setup.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import AppSetting


router = APIRouter(prefix="/api/settings", tags=["settings"])

env = get_settings()


class SettingsResponse(BaseModel):
    weekly_request_cap: int
    # Persona values here are already "effective" (DB override or .env fallback).
    persona_name: str
    persona_title: str
    persona_location: str
    persona_bio: str
    persona_interests: str


class SettingsUpdate(BaseModel):
    # All optional — only the provided fields are changed (partial update).
    weekly_request_cap: Optional[int] = Field(default=None, ge=1, le=1000)
    persona_name: Optional[str] = None
    persona_title: Optional[str] = None
    persona_location: Optional[str] = None
    persona_bio: Optional[str] = None
    persona_interests: Optional[str] = None


def effective_persona(setting: AppSetting) -> dict:
    """Return persona values: the stored value when set, else the .env fallback."""

    def pick(db_val: Optional[str], env_val: str) -> str:
        return db_val if (db_val is not None and db_val.strip() != "") else env_val

    return {
        "persona_name": pick(setting.persona_name, env.persona_name),
        "persona_title": pick(setting.persona_title, env.persona_title),
        "persona_location": pick(setting.persona_location, env.persona_location),
        "persona_bio": pick(setting.persona_bio, env.persona_bio),
        "persona_interests": pick(setting.persona_interests, env.persona_interests),
    }


def _to_response(setting: AppSetting) -> SettingsResponse:
    return SettingsResponse(
        weekly_request_cap=setting.weekly_request_cap,
        **effective_persona(setting),
    )


async def get_or_create_settings(db: AsyncSession) -> AppSetting:
    """Return the single settings row, creating a default one if none exists."""
    result = await db.execute(select(AppSetting).limit(1))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = AppSetting()
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return setting


@router.get("", response_model=SettingsResponse)
async def get_settings_route(db: AsyncSession = Depends(get_db)):
    """Get current settings (creates defaults on first call)."""
    setting = await get_or_create_settings(db)
    return _to_response(setting)


@router.patch("", response_model=SettingsResponse)
async def update_settings_route(
    update: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update any subset of settings (weekly cap and/or persona fields)."""
    setting = await get_or_create_settings(db)
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(setting, key, value)
    await db.commit()
    await db.refresh(setting)
    return _to_response(setting)
