from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from uuid import UUID
from datetime import date, datetime

class RouterNested(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)

class PlanNested(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)

class CustomerBase(BaseModel):
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    pppoe_username: str
    status: str = "ACTIVE"
    balance: float = 0.0
    router_id: UUID
    plan_id: UUID
    is_online: bool = False
    billing_day: int
    subscription_start: date
    subscription_end: date

class CustomerCreate(CustomerBase):
    pppoe_password: str

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    pppoe_username: Optional[str] = None
    pppoe_password: Optional[str] = None
    status: Optional[str] = None
    balance: Optional[float] = None
    router_id: Optional[UUID] = None
    plan_id: Optional[UUID] = None
    is_online: Optional[bool] = None
    billing_day: Optional[int] = None
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None

class CustomerResponse(CustomerBase):
    id: UUID
    mikrotik_secret_id: Optional[str] = None
    last_online_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    router: Optional[RouterNested] = None
    plan: Optional[PlanNested] = None

    model_config = ConfigDict(from_attributes=True)
