# SkyGate Backend Routes Map

Status labels:
- CORE_MVP: needed for the current frontend MVP.
- OPTIONAL: useful operational/support route, not required for core map/routing UX.
- REVIEW: relevant gap or contract that needs product/engineering review before frontend dependency.

| Method | Path | Endpoint file | Service called | Request schema | Response schema | Status |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/health` | `src/api/endpoints/health.py` | none | none | `HealthResponse` | OPTIONAL |
| GET | `/health/database` | `src/api/endpoints/health.py` | `DatabaseRepository.ping` | none | `DatabaseHealthResponse` | OPTIONAL |
| GET | `/airports/{slug}` | `src/api/endpoints/airports.py` | `AirportService.get_airport` | path `slug` | `AirportResponse` | CORE_MVP |
| GET | `/airports/{slug}/map` | `src/api/endpoints/airports.py` | `AirportService.get_map` | path `slug` | `AirportMapResponse` | CORE_MVP |
| POST | `/routes/calculate` | `src/api/endpoints/routes.py` | `RouteService.calculate` | `RouteRequest` | `RouteResponse` | CORE_MVP |

## MVP Flow Coverage

| Flow | Existing endpoint | Works by contract? | Needs adjustment? | Notes |
| --- | --- | --- | --- | --- |
| List airports | Missing | No | Yes | No `GET /airports` endpoint exists. Frontend must know `fortaleza` or a list endpoint must be added later. |
| Get airport by slug | `GET /airports/{slug}` | Yes | No | Returns airport metadata through `AirportResponse`. |
| Get graph nodes/edges by airport | `GET /airports/{slug}/map` | Yes | Review | Returns nodes, edges and businesses. `EdgeResponse` does not expose `edge_type`, `is_bidirectional`, or `is_estimated`; frontend may need these for rich route/map UI. |
| Search destinations/points | Partial via `GET /airports/{slug}/map` | Yes, with client filtering | Review | No dedicated search endpoint. Frontend can filter `nodes` locally for MVP if payload size remains acceptable. |
| Calculate route | `POST /routes/calculate` | Yes | Review | Calculates and persists a `route_session`. This is not read-only. |
| Calculate accessible route | `POST /routes/calculate` | Yes | No | Use `route_mode="accessible"`; schema sets `preferences.accessible = true`. |
| Return instructions/segments | `POST /routes/calculate` | Yes | No | `RouteResponse` includes `steps` and `floor_segments`. |

## Contract Notes

- `POST /routes/calculate` is a calculation endpoint but currently writes a route session through `RouteSessionRepository.create()`.
- Restricted destination behavior is unchanged and remains outside this audit.
- There is no root `GET /airports` list route yet.