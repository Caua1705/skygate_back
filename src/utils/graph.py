from collections import defaultdict
from typing import Any


def build_graph(edges: list[Any]) -> dict[str, list[dict]]:
    graph: dict[str, list[dict]] = defaultdict(list)
    for edge in edges:
        graph[str(edge.from_node_id)].append(
            {
                "to": str(edge.to_node_id),
                "weight": float(edge.walk_time_minutes),
                "instruction": edge.instruction,
            }
        )
        graph.setdefault(str(edge.to_node_id), [])
    return dict(graph)

