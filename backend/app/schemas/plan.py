from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class PlanBase(BaseModel):
    name: str
    mikrotik_profile_name: str
    download_speed_mbps: int
    upload_speed_mbps: int
    price: float = Field(..., gt=0)
    validity_days: int = 30
    is_active: bool = True

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    mikrotik_profile_name: Optional[str] = None
    download_speed_mbps: Optional[int] = None
    upload_speed_mbps: Optional[int] = None
    price: Optional[float] = None
    validity_days: Optional[int] = None
    is_active: Optional[bool] = None

class PlanResponse(PlanBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
