from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from src.schemas.airport_schema import AirportResponse


class NodeResponse(BaseModel):
    id: UUID
    code: str
    name: str
    type: str
    floor: str | None = None
    x: float | None = None
    y: float | None = None

    model_config = ConfigDict(from_attributes=True)


class EdgeResponse(BaseModel):
    id: UUID
    from_node_id: UUID
    to_node_id: UUID
    walk_time_minutes: float
    distance_meters: float | None = None
    instruction: str | None = None
    is_accessible: bool
    edge_type: str | None = None
    is_bidirectional: bool | None = None
    is_estimated: bool | None = None

    @computed_field
    @property
    def accessible(self) -> bool:
        return self.is_accessible

    @computed_field
    @property
    def weight_seconds(self) -> float:
        return round(float(self.walk_time_minutes) * 60, 2)

    model_config = ConfigDict(from_attributes=True)


class BusinessResponse(BaseModel):
    id: UUID
    node_id: UUID
    name: str
    category: str
    description: str | None = None
    estimated_stop_minutes: float
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AirportMapResponse(BaseModel):
    airport: AirportResponse
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
    businesses: list[BusinessResponse]

