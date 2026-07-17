"""Validate an airport graph JSON without touching the database."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DEFAULT_GRAPH_PATH = Path("data/airports/fortaleza/graph_v2.json")
CONNECTOR_TYPES = {"elevator", "stairs", "escalator"}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    totals: Counter = field(default_factory=Counter)

    @property
    def ok(self) -> bool:
        return not self.errors


def _node_key(node: dict[str, Any]) -> str | None:
    value = node.get("code") or node.get("id")
    return str(value).strip() if value is not None and str(value).strip() else None


def _edge_from(edge: dict[str, Any]) -> str | None:
    value = edge.get("from_node_id", edge.get("from_code"))
    return str(value).strip() if value is not None and str(value).strip() else None


def _edge_to(edge: dict[str, Any]) -> str | None:
    value = edge.get("to_node_id", edge.get("to_code"))
    return str(value).strip() if value is not None and str(value).strip() else None


def _edge_type(edge: dict[str, Any]) -> str:
    value = edge.get("type", edge.get("edge_type", "corridor"))
    return str(value).strip() if value is not None and str(value).strip() else "corridor"


def _business_node(business: dict[str, Any]) -> str | None:
    value = business.get("node_id", business.get("node_code"))
    return str(value).strip() if value is not None and str(value).strip() else None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _floor_number(node: dict[str, Any]) -> int | None:
    try:
        return int(str(node.get("floor")))
    except (TypeError, ValueError):
        return None


def validate_graph_data(data: Any) -> ValidationReport:
    report = ValidationReport()
    if not isinstance(data, dict):
        report.errors.append("JSON root must be an object")
        return report

    nodes = data.get("nodes")
    edges = data.get("edges")
    businesses = data.get("businesses", [])
    if not isinstance(nodes, list):
        report.errors.append("nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        report.errors.append("edges must be a list")
        edges = []
    if not isinstance(businesses, list):
        report.errors.append("businesses must be a list")
        businesses = []

    node_by_key: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            report.errors.append(f"node #{index} must be an object")
            continue
        key = _node_key(node)
        if key is None:
            report.errors.append(f"node #{index} is missing code/id")
            continue
        if key in node_by_key:
            report.errors.append(f"duplicate node key: {key}")
        node_by_key[key] = node

    seen_edges: set[tuple[str, str, str]] = set()
    connected_nodes: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            report.errors.append(f"edge #{index} must be an object")
            continue

        source = _edge_from(edge)
        target = _edge_to(edge)
        edge_type = _edge_type(edge)
        label = f"edge #{index} ({source!r} -> {target!r}, {edge_type})"

        if source is None:
            report.errors.append(f"{label}: from_node_id/from_code is missing")
        elif source not in node_by_key:
            report.errors.append(f"{label}: source node does not exist")

        if target is None:
            report.errors.append(f"{label}: to_node_id/to_code is missing")
        elif target not in node_by_key:
            report.errors.append(f"{label}: target node does not exist")

        if source is not None and target is not None:
            if source == target:
                report.errors.append(f"{label}: edge points to itself")
            duplicate_key = (source, target, edge_type)
            if duplicate_key in seen_edges:
                report.errors.append(f"{label}: duplicate edge")
            seen_edges.add(duplicate_key)
            connected_nodes.add(source)
            connected_nodes.add(target)

        weight = _decimal(edge.get("weight_seconds", edge.get("walk_time_seconds")))
        if weight is None or weight <= 0:
            report.errors.append(f"{label}: weight_seconds/walk_time_seconds must be positive")

        viewbox_distance = _decimal(edge.get("viewbox_distance"))
        if viewbox_distance is None:
            report.errors.append(f"{label}: viewbox_distance must be numeric")
        elif viewbox_distance < 0:
            report.errors.append(f"{label}: viewbox_distance cannot be negative")

    for index, business in enumerate(businesses):
        if not isinstance(business, dict):
            report.errors.append(f"business #{index} must be an object")
            continue
        node_key = _business_node(business)
        if node_key is None:
            report.errors.append(f"business #{index}: node_id/node_code is missing")
        elif node_key not in node_by_key:
            report.errors.append(f"business #{index}: node does not exist ({node_key})")

    for key in sorted(set(node_by_key) - connected_nodes):
        report.warnings.append(f"node has no edges: {key}")

    _validate_connectors(node_by_key, report)

    report.totals.update(
        nodes=len(node_by_key),
        edges=len(edges),
        businesses=len(businesses),
        errors=len(report.errors),
        warnings=len(report.warnings),
    )
    return report


def _validate_connectors(node_by_key: dict[str, dict[str, Any]], report: ValidationReport) -> None:
    groups: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    floors_with_vertical_connection: set[int] = set()
    floors = {floor for node in node_by_key.values() if (floor := _floor_number(node)) is not None}

    for key, node in node_by_key.items():
        connector_group = str(node.get("connector_group") or "").strip()
        if connector_group:
            groups[connector_group].append((key, node))

    for group, items in sorted(groups.items()):
        if len(items) == 1:
            report.warnings.append(f"connector_group has only one node: {group}")
            continue

        floors_in_group = {floor for _key, node in items if (floor := _floor_number(node)) is not None}
        if len(floors_in_group) <= 1:
            continue

        possible_pairs = []
        by_type: dict[str, set[int]] = defaultdict(set)
        for _key, node in items:
            node_type = str(node.get("type") or "").strip()
            floor = _floor_number(node)
            if node_type in CONNECTOR_TYPES and floor is not None:
                by_type[node_type].add(floor)

        for node_type, type_floors in by_type.items():
            for floor in sorted(type_floors):
                if floor + 1 in type_floors:
                    possible_pairs.append((node_type, floor, floor + 1))
                    floors_with_vertical_connection.update({floor, floor + 1})

        if not possible_pairs:
            listed_floors = ", ".join(str(item) for item in sorted(floors_in_group))
            report.errors.append(f"connector_group has multiple floors but no possible vertical connection: {group} ({listed_floors})")

    for floor in sorted(floors - floors_with_vertical_connection):
        report.warnings.append(f"floor has no vertical connection: {floor}")

    report.totals["connector_groups"] = len(groups)


def print_report(report: ValidationReport) -> None:
    if report.errors:
        print("Graph validation failed")
    elif report.warnings:
        print("Graph validation passed with warnings")
    else:
        print("Graph validation passed")

    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"WARNING: {message}")

    print(
        "Summary: "
        f"nodes={report.totals['nodes']}, "
        f"edges={report.totals['edges']}, "
        f"businesses={report.totals['businesses']}, "
        f"connector_groups={report.totals['connector_groups']}, "
        f"errors={len(report.errors)}, "
        f"warnings={len(report.warnings)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an airport graph JSON without database access.")
    parser.add_argument("json_path", nargs="?", type=Path, default=DEFAULT_GRAPH_PATH)
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read graph JSON: {exc}", file=sys.stderr)
        return 1

    report = validate_graph_data(data)
    print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())