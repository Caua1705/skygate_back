# SkyGate Backend MVP Status

## Final MVP Routes

- `GET /health`: optional liveness check.
- `GET /health/database`: optional database availability check.
- `GET /airports`: lists airport metadata without graph payload.
- `GET /airports/{slug}`: returns airport metadata by slug.
- `GET /airports/{slug}/map`: returns airport graph payload with nodes, edges and businesses.
- `POST /routes/calculate`: calculates normal, accessible and with-stop routes.

## MVP Route Assessment

| Flow | Status | Detail |
| --- | --- | --- |
| List airports | Present | `GET /airports`. |
| Get airport by slug | Present | `GET /airports/fortaleza`. |
| Get graph by airport | Present | `GET /airports/fortaleza/map`. |
| Search destinations/points | Partial | Use map nodes client-side for now; dedicated search is absent. |
| Calculate normal route | Present | `POST /routes/calculate` with `route_mode="fastest"`. |
| Calculate accessible route | Present | `POST /routes/calculate` with `route_mode="accessible"`. |
| Instructions/segments | Present | `RouteResponse.steps` and `RouteResponse.floor_segments`. |
| Route calculation without persistence | Present | `POST /routes/calculate` with `persist_session=false`. |

## Map Contract

`GET /airports/{slug}/map` keeps existing fields and exposes additional edge metadata:

- `edge_type`
- `is_bidirectional`
- `is_estimated`
- `is_accessible`
- `accessible`, derived from `is_accessible`
- `weight_seconds`, derived from `walk_time_minutes`

`viewbox_distance` is not exposed because it is not stored in the current database schema/model.

## Local Validation Result

- `py -m pytest`: passed with 61 tests.
- API started locally with `py -m uvicorn main:app --host 127.0.0.1 --port 8000`.
- `py scripts/smoke_test_backend_routes.py`: passed read-only HTTP routes and route calculation previews.
- `py scripts/smoke_test_backend_routes.py --allow-route-session-write`: passed route calculation with session persistence enabled.

## Smoke Test Results

Read-only smoke:

- `GET /health`: HTTP 200.
- `GET /health/database`: HTTP 200.
- `GET /airports`: HTTP 200.
- `GET /airports/fortaleza`: HTTP 200.
- `GET /airports/fortaleza/map`: HTTP 200, `nodes=233`, `edges=255`.
- `POST /routes/calculate` fastest with `persist_session=false`: HTTP 200, `path_nodes=16`.
- `POST /routes/calculate` accessible with `persist_session=false`: HTTP 200, `path_nodes=16`.
- `route_sessions` count stayed at 3 during read-only smoke.

Persistence smoke:

- `POST /routes/calculate` fastest with `persist_session=true`: HTTP 200, `path_nodes=16`.
- `POST /routes/calculate` accessible with `persist_session=true`: HTTP 200, `path_nodes=16`.
- `route_sessions` count increased from 3 to 5 during persistence smoke.

## Routes Absent

- Dedicated destinations/search endpoint.

## Remaining Frontend MVP Notes

- Frontend can use `GET /airports` for airport discovery.
- Frontend can use `GET /airports/fortaleza/map` and filter nodes client-side for destinations in the MVP.
- Frontend should call `POST /routes/calculate` with `persist_session=false` for preview/no-write route calculations.
- Use `persist_session=true` only when the product intentionally wants to save the route session.
- Restricted destination behavior remains unchanged and should be handled in the separate restricted-area task.