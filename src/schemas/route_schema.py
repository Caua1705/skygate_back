from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.constants import RouteMode, VALID_JOURNEY_TYPES, VALID_ROUTE_MODES
from src.schemas.airport_schema import AirportSummary


class RoutePreferences(BaseModel):
    accessible: bool = False
    avoid_stairs: bool = False
    business_id: UUID | None = None
    stop_category: str | None = None
    max_detour_minutes: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_single_stop_selection(self):
        if self.business_id is not None and self.stop_category is not None:
            raise ValueError("business_id and stop_category cannot be used together")
        return self


class RouteRequest(BaseModel):
    airport_slug: str
    journey_type: str = "boarding"
    origin_code: str
    destination_code: str
    boarding_time: datetime | None = None
    route_mode: str = RouteMode.FASTEST
    preferences: RoutePreferences | None = None
    persist_session: bool = True

    @field_validator("journey_type")
    @classmethod
    def validate_journey_type(cls, value: str) -> str:
        if value not in VALID_JOURNEY_TYPES:
            valid = ", ".join(sorted(VALID_JOURNEY_TYPES))
            raise ValueError(f"journey_type must be one of: {valid}")
        return value

    @field_validator("boarding_time")
    @classmethod
    def validate_boarding_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("boarding_time must include a timezone")
        return value

    @field_validator("route_mode")
    @classmethod
    def validate_route_mode(cls, value: str) -> str:
        if value not in VALID_ROUTE_MODES:
            valid = ", ".join(sorted(VALID_ROUTE_MODES))
            raise ValueError(f"route_mode must be one of: {valid}")
        return value

    @model_validator(mode="after")
    def apply_route_mode_rules(self):
        preferences = self.preferences or RoutePreferences()
        if self.route_mode == RouteMode.WITH_STOP and not (preferences.business_id or preferences.stop_category):
            raise ValueError("route_mode=with_stop requires business_id or stop_category")
        if self.route_mode == RouteMode.ACCESSIBLE:
            preferences.accessible = True
        self.preferences = preferences
        return self


class RoutePoint(BaseModel):
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoutePathNode(RoutePoint):
    type: str
    x: float | None = None
    y: float | None = None


class RouteServiceItem(BaseModel):
    name: str
    category: str
    estimated_stop_minutes: float


class SelectedBusinessResponse(RouteServiceItem):
    id: UUID
    node_id: UUID
    floor: str | None = None


class RouteResponse(BaseModel):
    airport: AirportSummary
    journey_type: str
    origin: RoutePoint
    destination: RoutePoint
    estimated_time_minutes: float
    free_time_minutes: float | None
    path: list[RoutePathNode]
    steps: list[str]
    services_on_path: list[RouteServiceItem]
    route_mode: str | None = None
    direct_estimated_time_minutes: float | None = None
    stop_time_minutes: float | None = None
    total_estimated_time_minutes: float | None = None
    detour_minutes: float | None = None
    stop_feasible: bool | None = None
    selected_business: SelectedBusinessResponse | None = None
    floor_segments: list[dict] | None = None
    warnings: list[dict] | None = None
