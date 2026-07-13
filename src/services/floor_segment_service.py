from typing import Any


class FloorSegmentService:
    def build(self, path: list[str], nodes_by_id: dict[str, Any], edges_by_pair: dict) -> list[dict]:
        if not path:
            return []

        segments: list[dict] = []
        current_floor = getattr(nodes_by_id[path[0]], "floor", None)
        current_nodes = [nodes_by_id[path[0]].code]

        for from_id, to_id in zip(path, path[1:]):
            node = nodes_by_id[to_id]
            next_floor = getattr(node, "floor", None)
            if next_floor == current_floor:
                current_nodes.append(node.code)
                continue

            segments.append({"floor": current_floor, "nodes": current_nodes})
            route_edge = edges_by_pair[(from_id, to_id)]
            segments.append(
                {
                    "transition": {
                        "type": getattr(route_edge.edge, "edge_type", "corridor"),
                        "from_floor": current_floor,
                        "to_floor": next_floor,
                    }
                }
            )
            current_floor = next_floor
            current_nodes = [node.code]

        segments.append({"floor": current_floor, "nodes": current_nodes})
        return segments
