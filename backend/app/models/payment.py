import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mpesa_receipt_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(15), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    transaction_date: Mapped[datetime] = mapped_column(DateTime)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)
    payment_method: Mapped[str] = mapped_column(String(20)) # STK_PUSH, C2B_PAYBILL
    checkout_request_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True) # PENDING, COMPLETED, FAILED
    reconciliation_status: Mapped[str] = mapped_column(String(30), default="MATCHED", index=True) # MATCHED, PENDING_REVIEW, MANUALLY_ASSIGNED
    bill_ref_number: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    matched_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    matched_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    raw_callback: Mapped[dict] = mapped_column(JSON, nullable=True)

    customer = relationship("Customer", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    matched_by = relationship("User", foreign_keys=[matched_by_user_id])

    __table_args__ = (
        Index("ix_payments_customer_created", "customer_id", "created_at"),
    )
