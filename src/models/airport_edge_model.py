from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class AirportEdge(Base):
    __tablename__ = "airport_edges"
    __table_args__ = (
        ForeignKeyConstraint(
            ["airport_id", "from_node_id"],
            ["airport_nodes.airport_id", "airport_nodes.id"],
            name="airport_edges_from_node_fk",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["airport_id", "to_node_id"],
            ["airport_nodes.airport_id", "airport_nodes.id"],
            name="airport_edges_to_node_fk",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "airport_id",
            "from_node_id",
            "to_node_id",
            name="airport_edges_airport_from_to_key",
        ),
        CheckConstraint(
            "walk_time_minutes >= 0",
            name="airport_edges_walk_time_non_negative",
        ),
        CheckConstraint(
            "distance_meters is null or distance_meters >= 0",
            name="airport_edges_distance_non_negative",
        ),
        CheckConstraint(
            "edge_type in ('corridor', 'ramp', 'stairs', 'escalator', 'elevator', 'security', 'boarding', 'restricted_transition')",
            name="airport_edges_edge_type_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    airport_id: Mapped[UUID] = mapped_column(ForeignKey("airports.id", ondelete="CASCADE"), nullable=False)
    from_node_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    to_node_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    walk_time_minutes: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric)
    instruction: Mapped[str | None] = mapped_column(Text)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    edge_type: Mapped[str] = mapped_column(Text, default="corridor", server_default="corridor")
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source_note: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    airport = relationship("Airport", back_populates="edges")
