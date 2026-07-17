from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AirportResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    city: str | None = None
    country: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AirportListItem(AirportResponse):
    is_active: bool | None = None


class AirportSummary(BaseModel):
    slug: str
    name: str

    model_config = ConfigDict(from_attributes=True)

