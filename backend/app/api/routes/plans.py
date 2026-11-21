from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from decimal import Decimal
import uuid
from app.api.deps import get_db, get_current_admin
from app.models import Plan

router = APIRouter()

class PlanCreate(BaseModel):
    name: str
    mikrotik_profile_name: str
    download_speed_mbps: int
    upload_speed_mbps: int
    price: Decimal
    validity_days: int
    is_active: bool = True

class PlanUpdate(BaseModel):
    name: str | None = None
    mikrotik_profile_name: str | None = None
    download_speed_mbps: int | None = None
    upload_speed_mbps: int | None = None
    price: Decimal | None = None
    validity_days: int | None = None
    is_active: bool | None = None

@router.get("/")
async def list_plans(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Plan))
    return result.scalars().all()

@router.post("/")
async def create_plan(data: PlanCreate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    new_plan = Plan(**data.dict())
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan

@router.patch("/{id}")
async def update_plan(id: uuid.UUID, data: PlanUpdate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Plan).where(Plan.id == id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    for key, value in data.dict(exclude_unset=True).items():
        setattr(plan, key, value)
        
    await db.commit()
    await db.refresh(plan)
    return plan

@router.delete("/{id}")
async def deactivate_plan(id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Plan).where(Plan.id == id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    plan.is_active = False
    await db.commit()
    return {"message": "Plan deactivated"}
