"""
Target Companies routes - manage companies for job search segment.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TargetCompany


router = APIRouter(prefix="/api/target-companies", tags=["target-companies"])


class TargetCompanyCreate(BaseModel):
    name: str
    notes: Optional[str] = None


class TargetCompanyResponse(BaseModel):
    id: UUID
    name: str
    notes: Optional[str]

    model_config = {"from_attributes": True}


@router.get("")
async def list_target_companies(db: AsyncSession = Depends(get_db)):
    """
    List all target companies.
    """
    stmt = select(TargetCompany).order_by(TargetCompany.name)
    result = await db.execute(stmt)
    companies = result.scalars().all()

    return [TargetCompanyResponse.model_validate(c) for c in companies]


@router.post("", response_model=TargetCompanyResponse)
async def create_target_company(
    company: TargetCompanyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new target company.
    """
    # Check if already exists
    stmt = select(TargetCompany).where(
        func.lower(TargetCompany.name) == company.name.lower()
    )
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Company already exists")

    new_company = TargetCompany(
        name=company.name,
        notes=company.notes,
    )
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)

    return TargetCompanyResponse.model_validate(new_company)


@router.post("/bulk")
async def create_target_companies_bulk(
    companies: list[TargetCompanyCreate],
    db: AsyncSession = Depends(get_db),
):
    """
    Add multiple target companies at once.
    """
    created = 0
    skipped = 0

    for company in companies:
        # Check if already exists
        stmt = select(TargetCompany).where(
            func.lower(TargetCompany.name) == company.name.lower()
        )
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        new_company = TargetCompany(
            name=company.name,
            notes=company.notes,
        )
        db.add(new_company)
        created += 1

    await db.commit()

    return {
        "status": "completed",
        "created": created,
        "skipped": skipped,
    }


@router.delete("/{company_id}")
async def delete_target_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a target company.
    """
    stmt = select(TargetCompany).where(TargetCompany.id == company_id)
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.delete(company)
    await db.commit()

    return {"status": "deleted", "name": company.name}
