from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import date, datetime

class CustomerNested(BaseModel):
    full_name: str
    model_config = ConfigDict(from_attributes=True)

class InvoiceBase(BaseModel):
    invoice_number: str
    customer_id: UUID
    amount: float
    due_date: date
    status: str = "PENDING"
    billing_period_start: date
    billing_period_end: date

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    customer_id: Optional[UUID] = None
    amount: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    paid_at: Optional[datetime] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None

class InvoiceResponse(InvoiceBase):
    id: UUID
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    customer: Optional[CustomerNested] = None

    model_config = ConfigDict(from_attributes=True)
