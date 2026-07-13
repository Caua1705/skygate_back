from dataclasses import dataclass
from typing import Any

from src.services.dijkstra_service import RouteNotFoundError
from src.services.waypoint_route_service import WaypointRoute, WaypointRouteService


class BusinessRouteNotFoundError(RouteNotFoundError):
    pass


@dataclass
class BusinessRouteRecommendation:
    business: Any
    route: WaypointRoute
    stop_time_minutes: float
    detour_minutes: float
    total_estimated_time_minutes: float


class BusinessRecommendationService:
    def __init__(self, waypoint_route_service: WaypointRouteService):
        self.waypoint_route_service = waypoint_route_service

    def calculate_for_business(
        self,
        business: Any,
        graph: dict[str, list[dict]],
        origin_id: str,
        destination_id: str,
        direct_walk_time_minutes: float,
        max_detour_minutes: float | None,
    ) -> BusinessRouteRecommendation:
        waypoint_id = str(getattr(business, "node_id", ""))
        if not waypoint_id or waypoint_id not in graph:
            raise BusinessRouteNotFoundError("Business does not have a valid navigation node")
        route = self.waypoint_route_service.calculate_with_waypoint(graph, origin_id, waypoint_id, destination_id)
        detour = max(0.0, route.walk_time_minutes - direct_walk_time_minutes)
        if max_detour_minutes is not None and detour > max_detour_minutes:
            raise BusinessRouteNotFoundError("Business exceeds max_detour_minutes")
        stop_time = float(getattr(business, "estimated_stop_minutes", 0) or 0)
        return BusinessRouteRecommendation(
            business=business,
            route=route,
            stop_time_minutes=stop_time,
            detour_minutes=detour,
            total_estimated_time_minutes=route.walk_time_minutes + stop_time,
        )

    def recommend_by_category(
        self,
        businesses: list[Any],
        graph: dict[str, list[dict]],
        origin_id: str,
        destination_id: str,
        direct_walk_time_minutes: float,
        max_detour_minutes: float | None,
    ) -> BusinessRouteRecommendation:
        candidates = []
        for business in businesses:
            try:
                candidates.append(
                    self.calculate_for_business(
                        business,
                        graph,
                        origin_id,
                        destination_id,
                        direct_walk_time_minutes,
                        max_detour_minutes,
                    )
                )
            except RouteNotFoundError:
                continue
        if not candidates:
            raise BusinessRouteNotFoundError("No eligible business route was found")
        return min(
            candidates,
            key=lambda candidate: (
                candidate.total_estimated_time_minutes,
                candidate.detour_minutes,
                str(candidate.business.id),
            ),
        )
