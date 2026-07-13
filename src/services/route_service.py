from src.core.constants import RouteMode
from src.repositories.airport_repository import AirportRepository
from src.repositories.business_repository import BusinessRepository
from src.repositories.graph_repository import GraphRepository
from src.repositories.route_session_repository import RouteSessionRepository
from src.schemas.route_schema import RouteRequest
from src.services.airport_service import AirportNotFoundError
from src.services.business_recommendation_service import (
    BusinessRecommendationService,
    BusinessRouteNotFoundError,
)
from src.services.dijkstra_service import DijkstraService
from src.services.floor_segment_service import FloorSegmentService
from src.services.graph_filter_service import FilteredGraph, GraphFilterService
from src.services.waypoint_route_service import WaypointRoute, WaypointRouteService
from src.utils.time import calculate_free_time_minutes, is_route_feasible


class NodeNotFoundError(Exception):
    pass


class BusinessNotFoundError(Exception):
    pass


class RouteService:
    def __init__(
        self,
        airport_repository: AirportRepository,
        graph_repository: GraphRepository,
        business_repository: BusinessRepository,
        route_session_repository: RouteSessionRepository,
        dijkstra_service: DijkstraService | None = None,
        graph_filter_service: GraphFilterService | None = None,
        waypoint_route_service: WaypointRouteService | None = None,
        business_recommendation_service: BusinessRecommendationService | None = None,
        floor_segment_service: FloorSegmentService | None = None,
    ):
        self.airport_repository = airport_repository
        self.graph_repository = graph_repository
        self.business_repository = business_repository
        self.route_session_repository = route_session_repository
        self.dijkstra_service = dijkstra_service or DijkstraService()
        self.graph_filter_service = graph_filter_service or GraphFilterService()
        self.waypoint_route_service = waypoint_route_service or WaypointRouteService(self.dijkstra_service)
        self.business_recommendation_service = business_recommendation_service or BusinessRecommendationService(
            self.waypoint_route_service
        )
        self.floor_segment_service = floor_segment_service or FloorSegmentService()

    def calculate(self, request: RouteRequest) -> dict:
        airport = self.airport_repository.get_by_slug(request.airport_slug)
        if airport is None:
            raise AirportNotFoundError(f"Airport '{request.airport_slug}' not found")

        nodes = self.graph_repository.list_nodes(airport.id)
        edges = self.graph_repository.list_edges(airport.id)
        nodes_by_code = {node.code: node for node in nodes}
        origin = nodes_by_code.get(request.origin_code)
        destination = nodes_by_code.get(request.destination_code)
        if origin is None or destination is None:
            missing = request.origin_code if origin is None else request.destination_code
            raise NodeNotFoundError(f"Node '{missing}' not found in airport '{airport.slug}'")

        preferences = request.preferences
        filtered_graph = self.graph_filter_service.build(
            nodes,
            edges,
            request.route_mode,
            preferences.accessible,
            preferences.avoid_stairs,
        )
        origin_id = str(origin.id)
        destination_id = str(destination.id)
        direct_route = self.waypoint_route_service.calculate_direct(filtered_graph.graph, origin_id, destination_id)
        selected_recommendation = self._select_stop_route(
            request,
            airport.id,
            filtered_graph,
            origin_id,
            destination_id,
            direct_route,
        )

        chosen_route = selected_recommendation.route if selected_recommendation else direct_route
        stop_time = selected_recommendation.stop_time_minutes if selected_recommendation else 0.0
        detour = selected_recommendation.detour_minutes if selected_recommendation else 0.0
        total_time = chosen_route.walk_time_minutes + stop_time
        stop_feasible = is_route_feasible(request.boarding_time, total_time) if selected_recommendation else None
        warnings = self._build_warnings(selected_recommendation is not None, stop_feasible)
        free_time = calculate_free_time_minutes(request.boarding_time, total_time)

        path_payload = self._build_path_payload(chosen_route.path, filtered_graph.nodes_by_id)
        steps = self._generate_steps(chosen_route.path, filtered_graph)
        services_payload = self._select_services_on_path(airport.id, chosen_route.path)
        floor_segments = self.floor_segment_service.build(
            chosen_route.path,
            filtered_graph.nodes_by_id,
            filtered_graph.edges_by_pair,
        )
        selected_business_payload = self._build_selected_business_payload(selected_recommendation)

        self.route_session_repository.create(
            airport_id=airport.id,
            origin_node_id=origin.id,
            destination_node_id=destination.id,
            journey_type=request.journey_type,
            boarding_time=request.boarding_time,
            estimated_time_minutes=chosen_route.walk_time_minutes,
            free_time_minutes=free_time,
            path=path_payload,
            services_on_path=services_payload,
            route_mode=request.route_mode,
            preferences=request.preferences.model_dump(mode="json"),
            selected_business_id=selected_recommendation.business.id if selected_recommendation else None,
            direct_estimated_time_minutes=direct_route.walk_time_minutes,
            stop_time_minutes=stop_time,
            total_estimated_time_minutes=total_time,
            detour_minutes=detour,
            stop_feasible=stop_feasible,
            floor_segments=floor_segments,
            warnings=warnings,
        )

        return {
            "airport": {"slug": airport.slug, "name": airport.name},
            "journey_type": request.journey_type,
            "origin": {"code": origin.code, "name": origin.name},
            "destination": {"code": destination.code, "name": destination.name},
            "estimated_time_minutes": round(chosen_route.walk_time_minutes, 2),
            "free_time_minutes": free_time,
            "path": path_payload,
            "steps": steps,
            "services_on_path": services_payload,
            "route_mode": request.route_mode,
            "direct_estimated_time_minutes": round(direct_route.walk_time_minutes, 2),
            "stop_time_minutes": round(stop_time, 2),
            "total_estimated_time_minutes": round(total_time, 2),
            "detour_minutes": round(detour, 2),
            "stop_feasible": stop_feasible,
            "selected_business": selected_business_payload,
            "floor_segments": floor_segments,
            "warnings": warnings,
        }

    def _select_stop_route(
        self,
        request: RouteRequest,
        airport_id,
        filtered_graph: FilteredGraph,
        origin_id: str,
        destination_id: str,
        direct_route: WaypointRoute,
    ):
        if request.route_mode != RouteMode.WITH_STOP:
            return None

        preferences = request.preferences
        if preferences.business_id is not None:
            business = self.business_repository.get_active_by_id_for_airport(preferences.business_id, airport_id)
            if business is None:
                raise BusinessNotFoundError("Active business not found for this airport")
            return self.business_recommendation_service.calculate_for_business(
                business,
                filtered_graph.graph,
                origin_id,
                destination_id,
                direct_route.walk_time_minutes,
                preferences.max_detour_minutes,
            )

        businesses = self.business_repository.list_active_by_category_for_airport(preferences.stop_category, airport_id)
        return self.business_recommendation_service.recommend_by_category(
            businesses,
            filtered_graph.graph,
            origin_id,
            destination_id,
            direct_route.walk_time_minutes,
            preferences.max_detour_minutes,
        )

    @staticmethod
    def _build_path_payload(path: list[str], nodes_by_id: dict) -> list[dict]:
        return [
            {
                "code": node.code,
                "name": node.name,
                "type": node.type,
                "x": float(node.x) if node.x is not None else None,
                "y": float(node.y) if node.y is not None else None,
            }
            for node in (nodes_by_id[node_id] for node_id in path)
        ]

    @staticmethod
    def _generate_steps(path: list[str], filtered_graph: FilteredGraph) -> list[str]:
        steps = []
        for from_id, to_id in zip(path, path[1:]):
            route_edge = filtered_graph.edges_by_pair[(from_id, to_id)]
            destination_name = filtered_graph.nodes_by_id[to_id].name
            steps.append(route_edge.instruction or f"Siga até {destination_name}.")
        return steps

    def _select_services_on_path(self, airport_id, path: list[str]) -> list[dict]:
        path_ids = set(path)
        businesses = self.business_repository.list_by_airport(airport_id)
        return [
            {
                "name": business.name,
                "category": business.category,
                "estimated_stop_minutes": float(business.estimated_stop_minutes),
            }
            for business in businesses
            if str(getattr(business, "node_id", "")) in path_ids
        ]

    @staticmethod
    def _build_selected_business_payload(recommendation) -> dict | None:
        if recommendation is None:
            return None
        business = recommendation.business
        return {
            "id": business.id,
            "node_id": business.node_id,
            "name": business.name,
            "category": business.category,
            "estimated_stop_minutes": float(business.estimated_stop_minutes),
            "floor": getattr(business, "floor", None),
        }

    @staticmethod
    def _build_warnings(has_stop: bool, stop_feasible: bool | None) -> list[dict]:
        if has_stop and stop_feasible is False:
            return [
                {
                    "code": "insufficient_time_for_stop",
                    "message": "The selected stop does not fit before boarding time.",
                }
            ]
        return []
