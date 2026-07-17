import importlib.util
import json
import sys
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("validate_airport_graph", Path("scripts/validate_airport_graph.py"))
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def valid_graph():
    return {
        "nodes": [
            {"code": "e0", "type": "elevator", "floor": "0", "connector_group": "elevador_a"},
            {"code": "e1", "type": "elevator", "floor": "1", "connector_group": "elevador_a"},
            {"code": "a", "type": "waypoint", "floor": "0", "connector_group": None},
            {"code": "b", "type": "waypoint", "floor": "1", "connector_group": None},
        ],
        "edges": [
            {"from_code": "a", "to_code": "e0", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
            {"from_code": "e0", "to_code": "e1", "edge_type": "elevator", "walk_time_seconds": 45, "viewbox_distance": 0},
            {"from_code": "e1", "to_code": "b", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
        ],
        "businesses": [{"node_code": "a", "name": "Cafe"}],
    }


def test_valid_graph_passes_without_errors_or_warnings():
    report = module.validate_graph_data(valid_graph())

    assert report.errors == []
    assert report.warnings == []
    assert report.ok is True


def test_detects_missing_nodes_self_edges_duplicates_and_bad_numbers():
    data = valid_graph()
    data["edges"] = [
        {"from_code": "missing", "to_code": "a", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
        {"from_code": "a", "to_code": "missing", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
        {"from_code": "a", "to_code": "a", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
        {"from_code": "a", "to_code": "b", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
        {"from_code": "a", "to_code": "b", "edge_type": "corridor", "walk_time_seconds": 10, "viewbox_distance": 10},
        {"from_code": "b", "to_code": "a", "edge_type": "corridor", "walk_time_seconds": 0, "viewbox_distance": -1},
    ]

    report = module.validate_graph_data(data)
    messages = "\n".join(report.errors)

    assert "source node does not exist" in messages
    assert "target node does not exist" in messages
    assert "edge points to itself" in messages
    assert "duplicate edge" in messages
    assert "weight_seconds/walk_time_seconds must be positive" in messages
    assert "viewbox_distance cannot be negative" in messages
    assert report.ok is False


def test_detects_business_with_missing_node():
    data = valid_graph()
    data["businesses"] = [{"node_code": "missing"}]

    report = module.validate_graph_data(data)

    assert any("business #0: node does not exist" in message for message in report.errors)


def test_warns_single_connector_group_node_and_isolated_node():
    data = valid_graph()
    data["nodes"].append({"code": "single", "type": "elevator", "floor": "0", "connector_group": "single_group"})

    report = module.validate_graph_data(data)
    warnings = "\n".join(report.warnings)

    assert "connector_group has only one node: single_group" in warnings
    assert "node has no edges: single" in warnings
    assert report.ok is True


def test_errors_when_connector_group_spans_floors_without_possible_vertical_connection():
    data = valid_graph()
    data["nodes"] = [
        {"code": "e0", "type": "elevator", "floor": "0", "connector_group": "mixed"},
        {"code": "s1", "type": "stairs", "floor": "1", "connector_group": "mixed"},
    ]
    data["edges"] = [
        {"from_code": "e0", "to_code": "s1", "edge_type": "corridor", "walk_time_seconds": 1, "viewbox_distance": 1},
    ]
    data["businesses"] = []

    report = module.validate_graph_data(data)

    assert any("multiple floors but no possible vertical connection" in message for message in report.errors)


def test_warns_floor_without_vertical_connection():
    data = valid_graph()
    data["nodes"].append({"code": "c", "type": "waypoint", "floor": "2", "connector_group": None})
    data["edges"].append({"from_code": "b", "to_code": "c", "edge_type": "corridor", "walk_time_seconds": 1, "viewbox_distance": 1})

    report = module.validate_graph_data(data)

    assert "floor has no vertical connection: 2" in report.warnings
    assert report.ok is True


def test_main_returns_zero_for_warnings_and_one_for_errors(tmp_path, capsys):
    warning_graph = valid_graph()
    warning_graph["nodes"].append({"code": "single", "type": "elevator", "floor": "0", "connector_group": "single_group"})
    warning_path = tmp_path / "warning.json"
    warning_path.write_text(json.dumps(warning_graph), encoding="utf-8")

    assert module.main([str(warning_path)]) == 0
    assert "Graph validation passed with warnings" in capsys.readouterr().out

    error_graph = valid_graph()
    error_graph["edges"][0]["to_code"] = "missing"
    error_path = tmp_path / "error.json"
    error_path.write_text(json.dumps(error_graph), encoding="utf-8")

    assert module.main([str(error_path)]) == 1
    assert "Graph validation failed" in capsys.readouterr().out