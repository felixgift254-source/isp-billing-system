import uuid
from datetime import date, datetime
from sqlalchemy import String, Integer, Numeric, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    pppoe_username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    pppoe_password: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True) # ACTIVE, SUSPENDED, EXPIRED, DISABLED
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    
    router_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("routers.id"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), index=True)
    
    mikrotik_secret_id: Mapped[str] = mapped_column(String(20), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_online_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    billing_day: Mapped[int] = mapped_column(Integer)
    subscription_start: Mapped[date] = mapped_column(Date)
    subscription_end: Mapped[date] = mapped_column(Date)
    grace_period_end: Mapped[date] = mapped_column(Date, nullable=True)

    router = relationship("Router", back_populates="customers")
    plan = relationship("Plan", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
