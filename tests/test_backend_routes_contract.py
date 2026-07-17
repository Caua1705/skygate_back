from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from src.api.dependencies.database import get_database
from src.api.endpoints import airports as airports_endpoint
from src.api.endpoints import routes as routes_endpoint
from src.schemas.graph_schema import EdgeResponse


def test_openapi_exposes_current_backend_mvp_routes():
    client = TestClient(app)

    paths = client.get("/openapi.json").json()["paths"]

    assert "get" in paths["/health"]
    assert "get" in paths["/health/database"]
    assert "get" in paths["/airports"]
    assert "get" in paths["/airports/{slug}"]
    assert "get" in paths["/airports/{slug}/map"]
    assert "post" in paths["/routes/calculate"]


def test_list_airports_endpoint_contract_without_database(monkeypatch):
    airport_id = uuid4()

    class FakeAirportService:
        def list_airports(self):
            return [
                SimpleNamespace(
                    id=airport_id,
                    slug="fortaleza",
                    name="Aeroporto de Fortaleza",
                    city="Fortaleza",
                    country="BR",
                )
            ]

    def fake_database():
        yield object()

    monkeypatch.setattr(airports_endpoint, "get_airport_service", lambda session: FakeAirportService())
    app.dependency_overrides[get_database] = fake_database
    try:
        response = TestClient(app).get("/airports")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(airport_id),
            "slug": "fortaleza",
            "name": "Aeroporto de Fortaleza",
            "city": "Fortaleza",
            "country": "BR",
            "is_active": None,
        }
    ]


def test_map_edge_response_includes_mvp_metadata():
    edge = SimpleNamespace(
        id=uuid4(),
        from_node_id=uuid4(),
        to_node_id=uuid4(),
        walk_time_minutes=1.5,
        distance_meters=None,
        instruction="Siga em frente.",
        is_accessible=True,
        edge_type="elevator",
        is_bidirectional=True,
        is_estimated=True,
    )

    data = EdgeResponse.model_validate(edge).model_dump(mode="json")

    assert data["edge_type"] == "elevator"
    assert data["is_bidirectional"] is True
    assert data["is_estimated"] is True
    assert data["is_accessible"] is True
    assert data["accessible"] is True
    assert data["weight_seconds"] == 90


def test_calculate_route_endpoint_contract_without_database_write(monkeypatch):
    calls = []

    class FakeRouteService:
        def __init__(self, *args, **kwargs):
            pass

        def calculate(self, request):
            calls.append(request.persist_session)
            return route_response(request)

    def fake_database():
        yield object()

    monkeypatch.setattr(routes_endpoint, "RouteService", FakeRouteService)
    app.dependency_overrides[get_database] = fake_database
    try:
        response = TestClient(app).post(
            "/routes/calculate",
            json={
                "airport_slug": "fortaleza",
                "journey_type": "boarding",
                "origin_code": "p0_porta_2",
                "destination_code": "p2_portao_18",
                "route_mode": "accessible",
                "persist_session": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == [False]
    data = response.json()
    assert data["airport"]["slug"] == "fortaleza"
    assert data["route_mode"] == "accessible"
    assert data["path"][0]["code"] == "p0_porta_2"
    assert data["steps"]
    assert "floor_segments" in data


def route_response(request):
    return {
        "airport": {"slug": request.airport_slug, "name": "Aeroporto de Fortaleza"},
        "journey_type": request.journey_type,
        "origin": {"code": request.origin_code, "name": "Porta 2"},
        "destination": {"code": request.destination_code, "name": "Portao 18"},
        "estimated_time_minutes": 12.5,
        "free_time_minutes": None,
        "path": [
            {"code": request.origin_code, "name": "Porta 2", "type": "entrance", "x": 1, "y": 2},
            {"code": request.destination_code, "name": "Portao 18", "type": "gate", "x": 3, "y": 4},
        ],
        "steps": ["Siga ate o destino."],
        "services_on_path": [],
        "route_mode": request.route_mode,
        "direct_estimated_time_minutes": 12.5,
        "stop_time_minutes": 0,
        "total_estimated_time_minutes": 12.5,
        "detour_minutes": 0,
        "stop_feasible": None,
        "selected_business": None,
        "floor_segments": [],
        "warnings": [],
    }