"""Smoke test existing SkyGate backend routes over HTTP.

By default route calculation is read-only because requests use
persist_session=false. Pass --allow-route-session-write to also test the
persisting behavior.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    core: bool = True


def _request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        raw = response.read().decode("utf-8")
        return response.status, json.loads(raw) if raw else {}


def _run_check(results: list[CheckResult], name: str, method: str, path: str, base_url: str, core: bool = True) -> Any | None:
    try:
        status, data = _request_json(base_url, method, path)
    except HTTPError as exc:
        results.append(CheckResult(name, False, f"HTTP {exc.code}", core))
        return None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        results.append(CheckResult(name, False, exc.__class__.__name__, core))
        return None

    ok = 200 <= status < 300
    results.append(CheckResult(name, ok, f"HTTP {status}", core))
    return data if ok else None


def _route_payload_from_map(map_data: dict[str, Any], accessible: bool, persist_session: bool) -> dict[str, Any] | None:
    codes = {node.get("code") for node in map_data.get("nodes", [])}
    origin = "p0_porta_2"
    destination = "p2_portao_18"
    if origin not in codes or destination not in codes:
        sorted_codes = sorted(code for code in codes if code)
        if len(sorted_codes) < 2:
            return None
        origin, destination = sorted_codes[0], sorted_codes[-1]

    return {
        "airport_slug": "fortaleza",
        "journey_type": "boarding",
        "origin_code": origin,
        "destination_code": destination,
        "route_mode": "accessible" if accessible else "fastest",
        "persist_session": persist_session,
    }


def _run_route_check(
    results: list[CheckResult],
    base_url: str,
    map_data: dict[str, Any],
    accessible: bool,
    persist_session: bool,
) -> None:
    payload = _route_payload_from_map(map_data, accessible=accessible, persist_session=persist_session)
    label = "POST /routes/calculate accessible" if accessible else "POST /routes/calculate fastest"
    label += " persist" if persist_session else " preview"
    if payload is None:
        results.append(CheckResult(label, False, "could not choose two valid nodes"))
        return

    try:
        status, data = _request_json(base_url, "POST", "/routes/calculate", payload)
    except HTTPError as exc:
        results.append(CheckResult(label, False, f"HTTP {exc.code}"))
        return
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        results.append(CheckResult(label, False, exc.__class__.__name__))
        return

    required = {"path", "steps", "floor_segments", "estimated_time_minutes"}
    missing = sorted(required - data.keys())
    if not (200 <= status < 300):
        results.append(CheckResult(label, False, f"HTTP {status}"))
    elif missing:
        results.append(CheckResult(label, False, f"missing response keys: {', '.join(missing)}"))
    elif not data["path"]:
        results.append(CheckResult(label, False, "empty path"))
    else:
        results.append(CheckResult(label, True, f"HTTP {status}, path_nodes={len(data['path'])}"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test SkyGate backend routes.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--allow-route-session-write",
        action="store_true",
        help="Also call POST /routes/calculate with persist_session=true.",
    )
    args = parser.parse_args(argv)

    results: list[CheckResult] = []
    _run_check(results, "GET /health", "GET", "/health", args.base_url, core=False)
    _run_check(results, "GET /health/database", "GET", "/health/database", args.base_url, core=False)
    airports = _run_check(results, "GET /airports", "GET", "/airports", args.base_url)
    airport = _run_check(results, "GET /airports/fortaleza", "GET", "/airports/fortaleza", args.base_url)
    map_data = _run_check(results, "GET /airports/fortaleza/map", "GET", "/airports/fortaleza/map", args.base_url)

    if airports is not None:
        has_fortaleza = any(item.get("slug") == "fortaleza" for item in airports if isinstance(item, dict))
        results.append(CheckResult("airport list includes fortaleza", has_fortaleza, f"airports={len(airports)}"))

    if airport and airport.get("slug") != "fortaleza":
        results.append(CheckResult("airport slug contract", False, "slug is not fortaleza"))

    if map_data:
        nodes = map_data.get("nodes", [])
        edges = map_data.get("edges", [])
        detail = f"nodes={len(nodes)}, edges={len(edges)}"
        results.append(CheckResult("map graph payload", bool(nodes and edges), detail))
        _run_route_check(results, args.base_url, map_data, accessible=False, persist_session=False)
        _run_route_check(results, args.base_url, map_data, accessible=True, persist_session=False)
        if args.allow_route_session_write:
            _run_route_check(results, args.base_url, map_data, accessible=False, persist_session=True)
            _run_route_check(results, args.base_url, map_data, accessible=True, persist_session=True)

    for result in results:
        status = "PASS" if result.ok else "FAIL"
        scope = "CORE" if result.core else "OPTIONAL"
        print(f"{status} [{scope}] {result.name}: {result.detail}")

    failed_core = [result for result in results if result.core and not result.ok]
    return 1 if failed_core else 0


if __name__ == "__main__":
    raise SystemExit(main())