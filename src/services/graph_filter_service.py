from dataclasses import dataclass
from typing import Any

from src.core.constants import EdgeType, RouteMode


@dataclass
class GraphRouteEdge:
    edge: Any
    instruction: str | None


@dataclass
class FilteredGraph:
    graph: dict[str, list[dict]]
    nodes_by_id: dict[str, Any]
    edges_by_pair: dict[tuple[str, str], GraphRouteEdge]


class GraphFilterService:
    def build(
        self,
        nodes: list[Any],
        edges: list[Any],
        route_mode: str,
        accessible: bool,
        avoid_stairs: bool,
    ) -> FilteredGraph:
        requires_accessible_route = route_mode == RouteMode.ACCESSIBLE or accessible
        nodes_by_id = {
            str(node.id): node
            for node in nodes
            if not getattr(node, "is_restricted", False)
            and (not requires_accessible_route or getattr(node, "is_accessible", True))
        }
        graph = {node_id: [] for node_id in nodes_by_id}
        edges_by_pair: dict[tuple[str, str], GraphRouteEdge] = {}

        for edge in edges:
            from_id = str(edge.from_node_id)
            to_id = str(edge.to_node_id)
            edge_type = getattr(edge, "edge_type", EdgeType.CORRIDOR)
            if from_id not in nodes_by_id or to_id not in nodes_by_id:
                continue
            if edge_type == EdgeType.STAIRS and (requires_accessible_route or avoid_stairs):
                continue
            if requires_accessible_route and not getattr(edge, "is_accessible", True):
                continue

            self._add_edge(graph, edges_by_pair, from_id, to_id, edge, getattr(edge, "instruction", None))
            if getattr(edge, "is_bidirectional", False):
                self._add_edge(graph, edges_by_pair, to_id, from_id, edge, None)

        for edge_list in graph.values():
            edge_list.sort(key=lambda item: item["to"])
        return FilteredGraph(graph=graph, nodes_by_id=nodes_by_id, edges_by_pair=edges_by_pair)

    @staticmethod
    def _add_edge(
        graph: dict[str, list[dict]],
        edges_by_pair: dict[tuple[str, str], GraphRouteEdge],
        from_id: str,
        to_id: str,
        edge: Any,
        instruction: str | None,
    ) -> None:
        graph[from_id].append({"to": to_id, "weight": float(edge.walk_time_minutes)})
        edges_by_pair[(from_id, to_id)] = GraphRouteEdge(edge=edge, instruction=instruction)
