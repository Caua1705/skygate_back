from dataclasses import dataclass

from src.services.dijkstra_service import DijkstraService


@dataclass
class WaypointRoute:
    path: list[str]
    walk_time_minutes: float


class WaypointRouteService:
    def __init__(self, dijkstra_service: DijkstraService):
        self.dijkstra_service = dijkstra_service

    def calculate_direct(self, graph: dict[str, list[dict]], origin_id: str, destination_id: str) -> WaypointRoute:
        result = self.dijkstra_service.calculate(graph, origin_id, destination_id)
        return WaypointRoute(path=result["path"], walk_time_minutes=float(result["total_time_minutes"]))

    def calculate_with_waypoint(
        self,
        graph: dict[str, list[dict]],
        origin_id: str,
        waypoint_id: str,
        destination_id: str,
    ) -> WaypointRoute:
        first_part = self.calculate_direct(graph, origin_id, waypoint_id)
        second_part = self.calculate_direct(graph, waypoint_id, destination_id)
        return WaypointRoute(
            path=first_part.path + second_part.path[1:],
            walk_time_minutes=first_part.walk_time_minutes + second_part.walk_time_minutes,
        )
