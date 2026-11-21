import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class Router(Base, TimestampMixin):
    __tablename__ = "routers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, index=True, nullable=False)
    api_port: Mapped[int] = mapped_column(Integer, default=443)
    api_username: Mapped[str] = mapped_column(String(100), nullable=False)
    api_password: Mapped[str] = mapped_column(Text, nullable=False) # Fernet encrypted
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OFFLINE") # ONLINE, OFFLINE, UNREACHABLE

    customers = relationship("Customer", back_populates="router")
