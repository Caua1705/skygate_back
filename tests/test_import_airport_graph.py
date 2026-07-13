import importlib.util
import sys
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location("import_airport_graph", Path("scripts/import_airport_graph.py"))
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def graph():
    return {
        "airport": {"slug": "fortaleza"},
        "nodes": [
            {"code": "a", "name": "A", "type": "waypoint", "floor": "0", "x": 1, "y": 2},
            {"code": "b", "name": "B", "type": "elevator", "floor": "1", "x": 3, "y": 4},
        ],
        "edges": [{"from_code": "a", "to_code": "b", "edge_type": "elevator", "walk_time_seconds": 30}],
        "businesses": [{"node_code": "a", "name": "Café", "category": "cafe"}],
    }


def test_validates_editor_export_format():
    assert module.validate_graph(graph())["airport"]["slug"] == "fortaleza"


def test_rejects_cross_floor_corridor():
    data = graph()
    data["edges"][0]["edge_type"] = "corridor"
    with pytest.raises(module.GraphValidationError, match="troca de piso"):
        module.validate_graph(data)


def test_rejects_duplicate_node_codes():
    data = graph()
    data["nodes"][1]["code"] = "a"
    with pytest.raises(module.GraphValidationError, match="duplicado"):
        module.validate_graph(data)
