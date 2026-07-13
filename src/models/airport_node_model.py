from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class AirportNode(Base):
    __tablename__ = "airport_nodes"
    __table_args__ = (
        UniqueConstraint("airport_id", "code", name="airport_nodes_airport_code_key"),
        UniqueConstraint("airport_id", "id", name="airport_nodes_airport_id_id_key"),
        CheckConstraint(
            "zone in ('public', 'checkin', 'security', 'domestic_airside', 'international_airside', 'connection', 'baggage_claim', 'restricted')",
            name="airport_nodes_zone_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    airport_id: Mapped[UUID] = mapped_column(ForeignKey("airports.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    floor: Mapped[str | None] = mapped_column(Text)
    x: Mapped[Decimal | None] = mapped_column(Numeric)
    y: Mapped[Decimal | None] = mapped_column(Numeric)
    zone: Mapped[str] = mapped_column(Text, default="public", server_default="public")
    connector_group: Mapped[str | None] = mapped_column(Text)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source_note: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    airport = relationship("Airport", back_populates="nodes")
