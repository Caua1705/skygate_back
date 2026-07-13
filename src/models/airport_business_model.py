from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class AirportBusiness(Base):
    __tablename__ = "airport_businesses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    airport_id: Mapped[UUID] = mapped_column(ForeignKey("airports.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[UUID] = mapped_column(ForeignKey("airport_nodes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    estimated_stop_minutes: Mapped[Decimal] = mapped_column(Numeric, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    external_id: Mapped[str | None] = mapped_column(Text)
    floor: Mapped[str | None] = mapped_column(Text)
    x: Mapped[Decimal | None] = mapped_column(Numeric)
    y: Mapped[Decimal | None] = mapped_column(Numeric)
    opening_hours: Mapped[dict | None] = mapped_column(JSONB)
    location_is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source_note: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    airport = relationship("Airport", back_populates="businesses")
