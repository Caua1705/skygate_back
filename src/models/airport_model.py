from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    city: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nodes = relationship("AirportNode", back_populates="airport", cascade="all, delete-orphan")
    edges = relationship("AirportEdge", back_populates="airport", cascade="all, delete-orphan")
    businesses = relationship("AirportBusiness", back_populates="airport", cascade="all, delete-orphan")

