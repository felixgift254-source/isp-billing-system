import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AuditLog(Base):
    """Immutable audit trail for all admin actions that affect customer accounts or finances."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Who performed the action
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email: Mapped[str] = mapped_column(String(200), nullable=True)  # denormalised for log durability

    # What was done
    action: Mapped[str] = mapped_column(String(80), index=True)   # e.g. SUSPEND, REACTIVATE, RECONCILE, PLAN_CHANGE
    target_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)  # e.g. Customer, Payment, Invoice
    target_id: Mapped[str] = mapped_column(String(80), nullable=True, index=True)    # UUID of the affected record

    # Extra context – arbitrary JSON payload
    details: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Network context
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)   # supports IPv6
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
