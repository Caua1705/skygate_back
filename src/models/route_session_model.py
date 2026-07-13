from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class RouteSession(Base):
    __tablename__ = "route_sessions"
    __table_args__ = (
        CheckConstraint(
            "route_mode in ('fastest', 'accessible', 'with_stop')",
            name="route_sessions_route_mode_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    airport_id: Mapped[UUID | None] = mapped_column(ForeignKey("airports.id"))
    origin_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("airport_nodes.id"))
    destination_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("airport_nodes.id"))
    journey_type: Mapped[str | None] = mapped_column(Text)
    boarding_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_time_minutes: Mapped[Decimal | None] = mapped_column(Numeric)
    free_time_minutes: Mapped[Decimal | None] = mapped_column(Numeric)
    path: Mapped[list | None] = mapped_column(JSONB)
    services_on_path: Mapped[list | None] = mapped_column(JSONB)
    route_mode: Mapped[str] = mapped_column(Text, nullable=False, default="fastest", server_default="fastest")
    preferences: Mapped[dict | None] = mapped_column(JSONB)
    selected_business_id: Mapped[UUID | None] = mapped_column(ForeignKey("airport_businesses.id"))
    direct_estimated_time_minutes: Mapped[Decimal | None] = mapped_column(Numeric)
    stop_time_minutes: Mapped[Decimal | None] = mapped_column(Numeric)
    total_estimated_time_minutes: Mapped[Decimal | None] = mapped_column(Numeric)
    detour_minutes: Mapped[Decimal | None] = mapped_column(Numeric)
    stop_feasible: Mapped[bool | None] = mapped_column(Boolean)
    floor_segments: Mapped[list | None] = mapped_column(JSONB)
    warnings: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
