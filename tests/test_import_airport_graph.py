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
        "estimated_seconds_per_viewbox_unit": 0.25,
        "time_estimation": {
            "method": "viewbox_distance * estimated_seconds_per_viewbox_unit",
            "is_estimated": True,
            "validated_on_site": False,
        },
        "nodes": [
            {"code": "a", "name": "A", "type": "waypoint", "floor": "0", "x": 1, "y": 2},
            {"code": "b", "name": "B", "type": "elevator", "floor": "1", "x": 3, "y": 4},
        ],
        "edges": [{
            "from_code": "a", "to_code": "b", "edge_type": "elevator",
            "viewbox_distance": 2.83, "distance_meters": None, "walk_time_seconds": 0.71,
            "is_accessible": True, "is_estimated": True,
        }],
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


def test_rejects_viewbox_units_exported_as_meters_or_unscaled_time():
    data = graph()
    data["edges"][0]["distance_meters"] = 2.83
    with pytest.raises(module.GraphValidationError, match="distance_meters deve ser null"):
        module.validate_graph(data)

    data = graph()
    data["edges"][0]["walk_time_seconds"] = 2.83
    with pytest.raises(module.GraphValidationError, match="walk_time_seconds deve ser 0.71"):
        module.validate_graph(data)


@pytest.mark.parametrize("node_type", ["stairs", "escalator"])
def test_rejects_accessible_edges_linked_to_stairs_or_escalators(node_type):
    data = graph()
    data["nodes"][1]["type"] = node_type
    data["edges"][0]["edge_type"] = node_type
    data["edges"][0]["is_accessible"] = True
    with pytest.raises(module.GraphValidationError, match="is_accessible deve ser false"):
        module.validate_graph(data)
