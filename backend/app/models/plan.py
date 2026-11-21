import uuid
from sqlalchemy import String, Integer, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    mikrotik_profile_name: Mapped[str] = mapped_column(String(100), index=True)
    download_speed_mbps: Mapped[int] = mapped_column(Integer)
    upload_speed_mbps: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    validity_days: Mapped[int] = mapped_column(Integer, default=30)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    customers = relationship("Customer", back_populates="plan")
