from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_all_routes_accept_cors_preflight_from_production_origins() -> None:
    for origin in ("https://gatesky.com.br", "https://www.gatesky.com.br"):
        for route in app.routes:
            for method in getattr(route, "methods", set()):
                response = client.options(
                    route.path,
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": method,
                    },
                )

                assert response.status_code == 200
                assert response.headers["access-control-allow-origin"] == origin


def test_route_response_returns_cors_header_for_production_origins() -> None:
    for origin in ("https://gatesky.com.br", "https://www.gatesky.com.br"):
        response = client.get("/health", headers={"Origin": origin})

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
