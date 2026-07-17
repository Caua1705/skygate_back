from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.core.constants import EdgeType, RouteMode
from src.schemas.route_schema import RouteRequest
from src.services.business_recommendation_service import (
    BusinessRecommendationService,
    BusinessRouteNotFoundError,
)
from src.services.dijkstra_service import DijkstraService, RouteNotFoundError
from src.services.floor_segment_service import FloorSegmentService
from src.services.graph_filter_service import GraphFilterService
from src.services.route_service import RouteService
from src.services.waypoint_route_service import WaypointRouteService


def make_node(code, floor="0", **overrides):
    data = {
        "id": uuid4(),
        "code": code,
        "name": code.replace("_", " ").title(),
        "type": "corridor",
        "floor": floor,
        "x": Decimal("0"),
        "y": Decimal("0"),
        "is_accessible": True,
        "is_restricted": False,
        "connector_group": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_edge(source, target, minutes, **overrides):
    data = {
        "id": uuid4(),
        "from_node_id": source.id,
        "to_node_id": target.id,
        "walk_time_minutes": Decimal(str(minutes)),
        "instruction": f"Siga até {target.name}.",
        "is_accessible": True,
        "is_bidirectional": False,
        "edge_type": EdgeType.CORRIDOR,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def build_filtered_graph(nodes, edges, route_mode=RouteMode.FASTEST, accessible=False, avoid_stairs=False):
    return GraphFilterService().build(nodes, edges, route_mode, accessible, avoid_stairs)


def test_legacy_request_defaults_to_fastest_mode():
    request = RouteRequest(
        airport_slug="fortaleza",
        journey_type="boarding",
        origin_code="entrada",
        destination_code="portao",
    )

    assert request.route_mode == RouteMode.FASTEST
    assert request.preferences.accessible is False


def test_route_request_validates_stop_preferences_and_accessible_mode():
    business_id = uuid4()
    with pytest.raises(ValidationError, match="requires business_id or stop_category"):
        RouteRequest(
            airport_slug="fortaleza", journey_type="boarding", origin_code="a", destination_code="b",
            route_mode=RouteMode.WITH_STOP,
        )
    with pytest.raises(ValidationError, match="cannot be used together"):
        RouteRequest(
            airport_slug="fortaleza", journey_type="boarding", origin_code="a", destination_code="b",
            preferences={"business_id": str(business_id), "stop_category": "cafe"},
        )

    request = RouteRequest(
        airport_slug="fortaleza", journey_type="boarding", origin_code="a", destination_code="b",
        route_mode=RouteMode.ACCESSIBLE,
    )
    assert request.preferences.accessible is True


def test_fastest_route_selects_lowest_weight_path():
    origin, short, long, destination = [make_node(code) for code in ("origem", "curto", "longo", "destino")]
    edges = [
        make_edge(origin, short, 1),
        make_edge(short, destination, 1),
        make_edge(origin, long, 1),
        make_edge(long, destination, 5),
    ]
    filtered = build_filtered_graph([origin, short, long, destination], edges)

    result = DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))

    assert result["path"] == [str(origin.id), str(short.id), str(destination.id)]


def test_unidirectional_edge_cannot_be_traversed_backwards():
    origin, destination = make_node("origem"), make_node("destino")
    filtered = build_filtered_graph([origin, destination], [make_edge(origin, destination, 1)])

    with pytest.raises(RouteNotFoundError):
        DijkstraService().calculate(filtered.graph, str(destination.id), str(origin.id))


def test_bidirectional_edge_can_be_traversed_backwards():
    origin, destination = make_node("origem"), make_node("destino")
    edge = make_edge(origin, destination, 1, is_bidirectional=True)
    filtered = build_filtered_graph([origin, destination], [edge])

    result = DijkstraService().calculate(filtered.graph, str(destination.id), str(origin.id))

    assert result["path"] == [str(destination.id), str(origin.id)]


def test_accessible_route_excludes_stairs_and_inaccessible_edges():
    origin, stairs_node, accessible_node, destination = [make_node(code) for code in ("origem", "escada", "rampa", "destino")]
    edges = [
        make_edge(origin, stairs_node, 1, edge_type=EdgeType.STAIRS),
        make_edge(stairs_node, destination, 1, edge_type=EdgeType.STAIRS),
        make_edge(origin, accessible_node, 2, edge_type=EdgeType.RAMP),
        make_edge(accessible_node, destination, 2, is_accessible=False),
    ]
    filtered = build_filtered_graph([origin, stairs_node, accessible_node, destination], edges, RouteMode.ACCESSIBLE, True)

    with pytest.raises(RouteNotFoundError):
        DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))


def test_avoid_stairs_excludes_only_stairs():
    origin, stairs_node, corridor_node, destination = [make_node(code) for code in ("origem", "escada", "corredor", "destino")]
    edges = [
        make_edge(origin, stairs_node, 1, edge_type=EdgeType.STAIRS),
        make_edge(stairs_node, destination, 1, edge_type=EdgeType.STAIRS),
        make_edge(origin, corridor_node, 2, is_accessible=False),
        make_edge(corridor_node, destination, 2, is_accessible=False),
    ]
    filtered = build_filtered_graph([origin, stairs_node, corridor_node, destination], edges, avoid_stairs=True)

    result = DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))

    assert result["path"] == [str(origin.id), str(corridor_node.id), str(destination.id)]


def test_floor_route_uses_real_elevator_edge_and_segments():
    origin = make_node("entrada", floor="0")
    elevator_p0 = make_node("elevador_p0", floor="0", connector_group="elevador_a")
    elevator_p2 = make_node("elevador_p2", floor="2", connector_group="elevador_a")
    destination = make_node("portao", floor="2")
    edges = [
        make_edge(origin, elevator_p0, 1),
        make_edge(elevator_p0, elevator_p2, 2, edge_type=EdgeType.ELEVATOR),
        make_edge(elevator_p2, destination, 1),
    ]
    filtered = build_filtered_graph([origin, elevator_p0, elevator_p2, destination], edges)
    result = DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))
    segments = FloorSegmentService().build(result["path"], filtered.nodes_by_id, filtered.edges_by_pair)

    assert any(item.get("transition", {}).get("type") == EdgeType.ELEVATOR for item in segments)
    assert segments[0]["floor"] == "0"
    assert segments[-1]["floor"] == "2"


def test_connector_group_without_vertical_edge_does_not_connect_floors():
    origin = make_node("origem", floor="0", connector_group="elevador_a")
    destination = make_node("destino", floor="2", connector_group="elevador_a")
    filtered = build_filtered_graph([origin, destination], [])

    with pytest.raises(RouteNotFoundError):
        DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))


def test_business_recommendation_selects_lowest_total_and_ignores_invalid_node():
    origin, shop_a_node, shop_b_node, destination = [make_node(code) for code in ("origem", "loja_a", "loja_b", "destino")]
    edges = [
        make_edge(origin, shop_a_node, 2), make_edge(shop_a_node, destination, 2),
        make_edge(origin, shop_b_node, 1), make_edge(shop_b_node, destination, 1),
    ]
    graph = build_filtered_graph([origin, shop_a_node, shop_b_node, destination], edges).graph
    businesses = [
        SimpleNamespace(id=uuid4(), node_id=shop_a_node.id, estimated_stop_minutes=Decimal("1")),
        SimpleNamespace(id=uuid4(), node_id=shop_b_node.id, estimated_stop_minutes=Decimal("4")),
        SimpleNamespace(id=uuid4(), node_id=None, estimated_stop_minutes=Decimal("0")),
    ]
    recommendation = BusinessRecommendationService(WaypointRouteService(DijkstraService())).recommend_by_category(
        businesses, graph, str(origin.id), str(destination.id), direct_walk_time_minutes=2, max_detour_minutes=None
    )

    assert recommendation.business.node_id == shop_a_node.id
    assert recommendation.total_estimated_time_minutes == 5


def test_business_respects_max_detour_and_never_becomes_graph_shortcut():
    origin, direct_node, shop_node, destination = [make_node(code) for code in ("origem", "direto", "loja", "destino")]
    edges = [
        make_edge(origin, direct_node, 1), make_edge(direct_node, destination, 1),
        make_edge(origin, shop_node, 5), make_edge(shop_node, destination, 5),
    ]
    filtered = build_filtered_graph([origin, direct_node, shop_node, destination], edges)
    direct = DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))
    business = SimpleNamespace(id=uuid4(), node_id=shop_node.id, estimated_stop_minutes=Decimal("1"))
    service = BusinessRecommendationService(WaypointRouteService(DijkstraService()))

    assert str(shop_node.id) not in direct["path"]
    with pytest.raises(BusinessRouteNotFoundError):
        service.calculate_for_business(business, filtered.graph, str(origin.id), str(destination.id), 2, 1)


class FakeAirportRepository:
    def __init__(self, airport):
        self.airport = airport

    def get_by_slug(self, slug):
        return self.airport if slug == self.airport.slug else None


class FakeGraphRepository:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

    def list_nodes(self, airport_id):
        return self.nodes

    def list_edges(self, airport_id):
        return self.edges


class FakeBusinessRepository:
    def __init__(self, businesses):
        self.businesses = businesses

    def list_by_airport(self, airport_id, active_only=True):
        return self.businesses

    def get_active_by_id_for_airport(self, business_id, airport_id):
        return next((business for business in self.businesses if business.id == business_id), None)

    def list_active_by_category_for_airport(self, category, airport_id):
        return [business for business in self.businesses if business.category == category]


class FakeRouteSessionRepository:
    def __init__(self):
        self.data = None

    def create(self, **data):
        self.data = data
        return SimpleNamespace(**data)


def test_route_service_specific_business_persists_metadata_and_warns_when_stop_is_late():
    airport = SimpleNamespace(id=uuid4(), slug="fortaleza", name="Fortaleza")
    origin, shop_node, destination = [make_node(code) for code in ("origem", "loja", "destino")]
    edges = [make_edge(origin, shop_node, 1), make_edge(shop_node, destination, 1)]
    business = SimpleNamespace(
        id=uuid4(), node_id=shop_node.id, name="Café", category="cafe", estimated_stop_minutes=Decimal("10"), floor="0"
    )
    sessions = FakeRouteSessionRepository()
    service = RouteService(
        FakeAirportRepository(airport), FakeGraphRepository([origin, shop_node, destination], edges),
        FakeBusinessRepository([business]), sessions
    )
    request = RouteRequest(
        airport_slug="fortaleza", journey_type="boarding", origin_code="origem", destination_code="destino",
        boarding_time=datetime.now(timezone.utc) + timedelta(minutes=1), route_mode=RouteMode.WITH_STOP,
        preferences={"business_id": str(business.id)},
    )

    response = service.calculate(request)

    assert response["selected_business"]["id"] == business.id
    assert [point["code"] for point in response["path"]] == ["origem", "loja", "destino"]
    assert response["stop_feasible"] is False
    assert response["warnings"][0]["code"] == "insufficient_time_for_stop"
    assert sessions.data["selected_business_id"] == business.id
    assert sessions.data["floor_segments"]



def test_accessible_floor_route_uses_elevator_and_avoids_stairs_or_escalators():
    origin = make_node("entrada", floor="0")
    elevator_p0 = make_node("elevador_p0", floor="0", type="elevator", connector_group="elevador_a")
    elevator_p1 = make_node("elevador_p1", floor="1", type="elevator", connector_group="elevador_a")
    stairs_p0 = make_node("escada_p0", floor="0", type="stairs", is_accessible=False, connector_group="escada_a")
    stairs_p1 = make_node("escada_p1", floor="1", type="stairs", is_accessible=False, connector_group="escada_a")
    escalator_p0 = make_node("rolante_p0", floor="0", type="escalator", is_accessible=False, connector_group="rolante_a")
    escalator_p1 = make_node("rolante_p1", floor="1", type="escalator", is_accessible=False, connector_group="rolante_a")
    destination = make_node("destino", floor="1")
    edges = [
        make_edge(origin, elevator_p0, 1),
        make_edge(elevator_p0, elevator_p1, 1, edge_type=EdgeType.ELEVATOR, is_accessible=True, is_bidirectional=True),
        make_edge(elevator_p1, destination, 1),
        make_edge(origin, stairs_p0, 1, is_accessible=False),
        make_edge(stairs_p0, stairs_p1, 1, edge_type=EdgeType.STAIRS, is_accessible=False, is_bidirectional=True),
        make_edge(stairs_p1, destination, 1, is_accessible=False),
        make_edge(origin, escalator_p0, 1, is_accessible=False),
        make_edge(escalator_p0, escalator_p1, 1, edge_type=EdgeType.ESCALATOR, is_accessible=False, is_bidirectional=True),
        make_edge(escalator_p1, destination, 1, is_accessible=False),
    ]
    filtered = build_filtered_graph(
        [origin, elevator_p0, elevator_p1, stairs_p0, stairs_p1, escalator_p0, escalator_p1, destination],
        edges,
        route_mode=RouteMode.ACCESSIBLE,
        accessible=True,
    )

    result = DijkstraService().calculate(filtered.graph, str(origin.id), str(destination.id))
    path_codes = [filtered.nodes_by_id[node_id].code for node_id in result["path"]]

    assert path_codes == ["entrada", "elevador_p0", "elevador_p1", "destino"]
    assert "escada_p0" not in path_codes
    assert "rolante_p0" not in path_codes


def build_fortaleza_filtered_graph(accessible=False):
    import importlib.util
    import json
    import sys
    from pathlib import Path
    from uuid import NAMESPACE_URL, uuid5

    spec = importlib.util.spec_from_file_location("import_airport_graph_routes", Path("scripts/import_airport_graph.py"))
    importer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = importer
    assert spec.loader is not None
    spec.loader.exec_module(importer)

    data = json.loads(Path("data/airports/fortaleza/graph_v2.json").read_text(encoding="utf-8"))
    importer.validate_graph(data)
    node_ids = {row["code"]: uuid5(NAMESPACE_URL, row["code"]) for row in data["nodes"]}
    nodes = [
        SimpleNamespace(
            id=node_ids[row["code"]],
            code=row["code"],
            name=row["name"],
            type=row["type"],
            floor=str(row["floor"]),
            x=Decimal(str(row["x"])),
            y=Decimal(str(row["y"])),
            is_accessible=bool(row.get("is_accessible", True)),
            is_restricted=bool(row.get("is_restricted", False)),
            connector_group=row.get("connector_group"),
        )
        for row in data["nodes"]
    ]
    edges = [
        SimpleNamespace(
            id=uuid5(NAMESPACE_URL, f"{row['from_code']}->{row['to_code']}"),
            from_node_id=node_ids[row["from_code"]],
            to_node_id=node_ids[row["to_code"]],
            walk_time_minutes=Decimal(str(row["walk_time_seconds"])) / Decimal(60),
            instruction=row.get("instruction"),
            is_accessible=bool(row.get("is_accessible", True)),
            is_bidirectional=bool(row.get("is_bidirectional", False)),
            edge_type=row.get("edge_type", EdgeType.CORRIDOR),
        )
        for row in [*data["edges"], *importer.build_vertical_connector_edges(data)]
    ]
    filtered = build_filtered_graph(
        nodes,
        edges,
        route_mode=RouteMode.ACCESSIBLE if accessible else RouteMode.FASTEST,
        accessible=accessible,
    )
    return filtered, {node.code: node for node in nodes}


@pytest.mark.parametrize(
    ("origin_code", "destination_code"),
    [
        ("p0_porta_2", "p2_portao_18"),
        ("p0_corredor_acesso_terminal", "p1_corredor_acesso_externo"),
        ("p1_elevador_b", "p3_elevador_b"),
        ("p2_portao_1", "p2_portao_28"),
        ("p2_pague_menos", "p2_wc_pier_leste"),
    ],
)
def test_fortaleza_graph_scenarios_are_routable_after_vertical_generation(origin_code, destination_code):
    filtered, nodes_by_code = build_fortaleza_filtered_graph()

    result = DijkstraService().calculate(
        filtered.graph,
        str(nodes_by_code[origin_code].id),
        str(nodes_by_code[destination_code].id),
    )
    path_codes = [filtered.nodes_by_id[node_id].code for node_id in result["path"]]

    assert path_codes[0] == origin_code
    assert path_codes[-1] == destination_code


@pytest.mark.parametrize(
    ("origin_code", "destination_code"),
    [
        ("p0_porta_2", "p2_portao_18"),
        ("p0_corredor_acesso_terminal", "p1_corredor_acesso_externo"),
        ("p1_elevador_b", "p3_elevador_b"),
    ],
)
def test_fortaleza_accessible_vertical_routes_use_elevators(origin_code, destination_code):
    filtered, nodes_by_code = build_fortaleza_filtered_graph(accessible=True)

    result = DijkstraService().calculate(
        filtered.graph,
        str(nodes_by_code[origin_code].id),
        str(nodes_by_code[destination_code].id),
    )
    edge_types = [
        filtered.edges_by_pair[(source_id, target_id)].edge.edge_type
        for source_id, target_id in zip(result["path"], result["path"][1:])
    ]

    assert EdgeType.ELEVATOR in edge_types
    assert EdgeType.STAIRS not in edge_types
    assert EdgeType.ESCALATOR not in edge_types