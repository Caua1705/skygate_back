from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from src.schemas.route_schema import RouteRequest
from src.services.route_service import RouteService


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


class FakeRouteSessionRepository:
    def __init__(self):
        self.saved_data = None

    def create(self, **data):
        self.saved_data = data
        return SimpleNamespace(**data)


def test_route_service_calculates_and_saves_route():
    airport_id = uuid4()
    origin_id = uuid4()
    corridor_id = uuid4()
    destination_id = uuid4()
    off_route_id = uuid4()
    airport = SimpleNamespace(id=airport_id, slug="fortaleza", name="Aeroporto de Fortaleza")
    nodes = [
        SimpleNamespace(id=origin_id, code="entrada", name="Entrada", type="entrance", x=0, y=0),
        SimpleNamespace(id=corridor_id, code="corredor", name="Corredor", type="corridor", x=1, y=1),
        SimpleNamespace(id=destination_id, code="portao", name="Portão", type="gate", x=2, y=2),
        SimpleNamespace(id=off_route_id, code="ala_leste", name="Ala leste", type="corridor", x=3, y=1),
    ]
    edges = [
        SimpleNamespace(
            from_node_id=origin_id,
            to_node_id=corridor_id,
            walk_time_minutes=Decimal("2"),
            instruction="Siga até o corredor.",
        ),
        SimpleNamespace(
            from_node_id=corridor_id,
            to_node_id=destination_id,
            walk_time_minutes=Decimal("3"),
            instruction="Continue até o portão.",
        ),
        SimpleNamespace(
            from_node_id=corridor_id,
            to_node_id=off_route_id,
            walk_time_minutes=Decimal("1"),
            instruction="Siga até a ala leste.",
        ),
    ]
    businesses = [
        SimpleNamespace(
            node_id=corridor_id,
            name="Café Central",
            category="cafe",
            estimated_stop_minutes=Decimal("5"),
        ),
        SimpleNamespace(
            node_id=off_route_id,
            name="Loja da Ala Leste",
            category="shopping",
            estimated_stop_minutes=Decimal("4"),
        ),
    ]
    session_repository = FakeRouteSessionRepository()
    service = RouteService(
        FakeAirportRepository(airport),
        FakeGraphRepository(nodes, edges),
        FakeBusinessRepository(businesses),
        session_repository,
    )

    response = service.calculate(
        RouteRequest(
            airport_slug="fortaleza",
            journey_type="boarding",
            origin_code="entrada",
            destination_code="portao",
        )
    )

    assert response["estimated_time_minutes"] == 5
    assert [node["code"] for node in response["path"]] == ["entrada", "corredor", "portao"]
    assert all(node["type"] != "service" for node in response["path"])
    assert response["steps"] == ["Siga até o corredor.", "Continue até o portão."]
    assert [service["name"] for service in response["services_on_path"]] == ["Café Central"]
    assert session_repository.saved_data["estimated_time_minutes"] == 5

