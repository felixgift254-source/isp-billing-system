from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

class CustomerNestedPayment(BaseModel):
    full_name: str
    model_config = ConfigDict(from_attributes=True)

class InvoiceNestedPayment(BaseModel):
    invoice_number: str
    model_config = ConfigDict(from_attributes=True)

class PaymentBase(BaseModel):
    mpesa_receipt_number: Optional[str] = None
    phone_number: str
    amount: float
    transaction_date: datetime
    invoice_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    payment_method: str
    checkout_request_id: Optional[str] = None
    status: str = "PENDING"
    reconciliation_status: str = "MATCHED"
    bill_ref_number: Optional[str] = None
    matched_by_user_id: Optional[UUID] = None
    matched_at: Optional[datetime] = None

class PaymentReconcileRequest(BaseModel):
    customer_id: UUID
    invoice_id: Optional[UUID] = None

class PaymentUpdate(BaseModel):
    mpesa_receipt_number: Optional[str] = None
    phone_number: Optional[str] = None
    amount: Optional[float] = None
    transaction_date: Optional[datetime] = None
    invoice_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    payment_method: Optional[str] = None
    checkout_request_id: Optional[str] = None
    status: Optional[str] = None
    raw_callback: Optional[dict[str, Any]] = None

class PaymentResponse(PaymentBase):
    id: UUID
    raw_callback: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    customer: Optional[CustomerNestedPayment] = None
    invoice: Optional[InvoiceNestedPayment] = None

    model_config = ConfigDict(from_attributes=True)
