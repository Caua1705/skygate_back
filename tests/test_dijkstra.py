from math import inf, nan

import pytest

from src.services.dijkstra_service import DijkstraService, InvalidEdgeWeightError, RouteNotFoundError


def test_dijkstra_finds_shortest_path():
    graph = {
        "a": [{"to": "b", "weight": 2}, {"to": "c", "weight": 10}],
        "b": [{"to": "c", "weight": 3}],
        "c": [],
    }

    result = DijkstraService().calculate(graph, "a", "c")

    assert result["path"] == ["a", "b", "c"]
    assert result["total_time_minutes"] == 5


def test_dijkstra_raises_when_route_is_impossible():
    graph = {"a": [], "b": []}

    with pytest.raises(RouteNotFoundError):
        DijkstraService().calculate(graph, "a", "b")


def test_dijkstra_handles_same_origin_and_destination():
    result = DijkstraService().calculate({"a": []}, "a", "a")

    assert result == {"path": ["a"], "total_time_minutes": 0.0}


def test_dijkstra_rejects_negative_weight():
    graph = {"a": [{"to": "b", "weight": -1}], "b": []}

    with pytest.raises(InvalidEdgeWeightError, match="negative"):
        DijkstraService().calculate(graph, "a", "b")


@pytest.mark.parametrize("invalid_weight", [nan, inf, -inf])
def test_dijkstra_rejects_non_finite_weight(invalid_weight):
    graph = {"a": [{"to": "b", "weight": invalid_weight}], "b": []}

    with pytest.raises(InvalidEdgeWeightError, match="non-finite"):
        DijkstraService().calculate(graph, "a", "b")


def test_dijkstra_rejects_non_numeric_weight():
    graph = {"a": [{"to": "b", "weight": "2"}], "b": []}

    with pytest.raises(InvalidEdgeWeightError, match="non-numeric"):
        DijkstraService().calculate(graph, "a", "b")
