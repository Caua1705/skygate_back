import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

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



def connector_graph():
    data = graph()
    data["nodes"] = [
        {"code": "e0", "name": "E0", "type": "elevator", "floor": "0", "x": 0, "y": 0, "connector_group": "elevador_x"},
        {"code": "e1", "name": "E1", "type": "elevator", "floor": "1", "x": 0, "y": 0, "connector_group": "elevador_x"},
        {"code": "e2", "name": "E2", "type": "elevator", "floor": "2", "x": 0, "y": 0, "connector_group": "elevador_x"},
        {"code": "s0", "name": "S0", "type": "stairs", "floor": "0", "x": 0, "y": 0, "connector_group": "escada_x"},
        {"code": "s1", "name": "S1", "type": "stairs", "floor": "1", "x": 0, "y": 0, "connector_group": "escada_x"},
        {"code": "r0", "name": "R0", "type": "escalator", "floor": "0", "x": 0, "y": 0, "connector_group": "rolante_x"},
        {"code": "r1", "name": "R1", "type": "escalator", "floor": "1", "x": 0, "y": 0, "connector_group": "rolante_x"},
        {"code": "n0", "name": "N0", "type": "elevator", "floor": "0", "x": 0, "y": 0, "connector_group": None},
        {"code": "m0", "name": "M0", "type": "elevator", "floor": "0", "x": 0, "y": 0, "connector_group": "misto"},
        {"code": "m1", "name": "M1", "type": "stairs", "floor": "1", "x": 0, "y": 0, "connector_group": "misto"},
        {"code": "skip0", "name": "Skip0", "type": "elevator", "floor": "0", "x": 0, "y": 0, "connector_group": "skip"},
        {"code": "skip2", "name": "Skip2", "type": "elevator", "floor": "2", "x": 0, "y": 0, "connector_group": "skip"},
    ]
    data["edges"] = []
    data["businesses"] = []
    return data


def test_connector_group_generates_only_consecutive_vertical_edges():
    edges = module.build_vertical_connector_edges(connector_graph())
    pairs = {(edge["from_code"], edge["to_code"]) for edge in edges}

    assert ("e0", "e1") in pairs
    assert ("e1", "e2") in pairs
    assert ("e0", "e2") not in pairs
    assert ("skip0", "skip2") not in pairs


def test_connector_group_sets_vertical_edge_metadata_by_type():
    edges = {edge["from_code"]: edge for edge in module.build_vertical_connector_edges(connector_graph())}

    assert edges["e0"]["edge_type"] == "elevator"
    assert edges["e0"]["walk_time_seconds"] == module.Decimal("45")
    assert edges["e0"]["is_accessible"] is True
    assert edges["e0"]["is_bidirectional"] is True
    assert edges["e0"]["viewbox_distance"] == 0

    assert edges["s0"]["edge_type"] == "stairs"
    assert edges["s0"]["walk_time_seconds"] == module.Decimal("35")
    assert edges["s0"]["is_accessible"] is False

    assert edges["r0"]["edge_type"] == "escalator"
    assert edges["r0"]["walk_time_seconds"] == module.Decimal("30")
    assert edges["r0"]["is_accessible"] is False


def test_connector_group_ignores_null_groups_mixed_types_and_duplicates():
    data = connector_graph()
    data["edges"] = [{
        "from_code": "e0", "to_code": "e1", "edge_type": "elevator",
        "viewbox_distance": 0, "distance_meters": None, "walk_time_seconds": 45,
        "is_accessible": True, "is_estimated": True,
    }]

    pairs = {(edge["from_code"], edge["to_code"]) for edge in module.build_vertical_connector_edges(data)}

    assert ("n0", "n0") not in pairs
    assert ("m0", "m1") not in pairs
    assert ("e0", "e1") not in pairs
    assert ("e1", "e0") not in pairs


class FakeDeleteResult:
    rowcount = 2


class FakeDeleteSession:
    def __init__(self):
        self.tables = []

    def execute(self, statement):
        self.tables.append(statement.table.name)
        return FakeDeleteResult()


def test_replace_delete_order_respects_foreign_keys():
    counts = module.Counts()
    session = FakeDeleteSession()

    module._delete_airport_graph(session, "00000000-0000-0000-0000-000000000001", counts)

    assert session.tables == ["route_sessions", "airport_businesses", "airport_edges", "airport_nodes"]
    assert counts.deleted["route_sessions"] == 2
    assert counts.deleted["businesses"] == 2
    assert counts.deleted["edges"] == 2
    assert counts.deleted["nodes"] == 2


def test_main_passes_replace_and_dry_run_flags(monkeypatch, tmp_path):
    json_path = tmp_path / "graph.json"
    json_path.write_text("{}", encoding="utf-8")
    calls = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def begin(self):
            return self

    def fake_session_local():
        return FakeSession()

    def fake_import_graph(session, data, *, dry_run=False, replace=False):
        calls["dry_run"] = dry_run
        calls["replace"] = replace
        return module.Counts()

    monkeypatch.setattr(module, "SessionLocal", fake_session_local)
    monkeypatch.setattr(module, "validate_graph", lambda data: data)
    monkeypatch.setattr(module, "import_graph", fake_import_graph)
    monkeypatch.setattr(module.sys, "argv", ["import_airport_graph.py", str(json_path), "--replace", "--dry-run"])

    assert module.main() == 0
    assert calls == {"dry_run": True, "replace": True}


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)


class FakeImportSession:
    def __init__(self):
        self.airport = type("Airport", (), {"id": uuid4(), "slug": "fortaleza"})()
        self.scalars_calls = 0
        self.added = []
        self.rollback_called = False
        self.execute_called = False

    def scalar(self, statement):
        return self.airport if not self.added else None

    def scalars(self, statement):
        self.scalars_calls += 1
        return FakeScalarResult([])

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()

    def rollback(self):
        self.rollback_called = True

    def execute(self, statement):
        self.execute_called = True
        return FakeDeleteResult()


def test_import_graph_dry_run_rolls_back_and_incremental_does_not_delete():
    session = FakeImportSession()

    counts = module.import_graph(session, graph(), dry_run=True)

    assert session.rollback_called is True
    assert session.execute_called is False
    assert counts.inserted["nodes"] == 2
    assert counts.inserted["edges"] == 1
    assert counts.inserted["businesses"] == 1


def test_replace_dry_run_deletes_then_rolls_back_without_commit():
    session = FakeImportSession()

    counts = module.import_graph(session, graph(), dry_run=True, replace=True)

    assert session.execute_called is True
    assert session.rollback_called is True
    assert counts.deleted["route_sessions"] == 2
    assert counts.deleted["businesses"] == 2
    assert counts.deleted["edges"] == 2
    assert counts.deleted["nodes"] == 2


def test_main_transaction_context_rolls_back_on_import_error(monkeypatch, tmp_path):
    json_path = tmp_path / "graph.json"
    json_path.write_text("{}", encoding="utf-8")
    state = {"rolled_back": False}

    class FakeTransaction:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            state["rolled_back"] = exc_type is not None
            return False

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def begin(self):
            return FakeTransaction()

    monkeypatch.setattr(module, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(module, "validate_graph", lambda data: data)

    def fail_import(session, data, *, dry_run=False, replace=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "import_graph", fail_import)
    monkeypatch.setattr(module.sys, "argv", ["import_airport_graph.py", str(json_path), "--replace"])

    assert module.main() == 1
    assert state["rolled_back"] is True
