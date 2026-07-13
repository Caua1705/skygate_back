import heapq
from decimal import Decimal
from math import inf, isfinite


class RouteNotFoundError(Exception):
    pass


class InvalidEdgeWeightError(ValueError):
    pass


class DijkstraService:
    def calculate(self, graph: dict[str, list[dict]], origin: str, destination: str) -> dict:
        self._validate_weights(graph)

        if origin not in graph or destination not in graph:
            raise RouteNotFoundError("Origin or destination is not present in the graph")

        distances = {node: inf for node in graph}
        previous: dict[str, str] = {}
        distances[origin] = 0.0
        queue = [(0.0, origin)]

        while queue:
            current_distance, current_node = heapq.heappop(queue)
            if current_distance > distances[current_node]:
                continue
            if current_node == destination:
                break

            for edge in graph[current_node]:
                neighbor = edge["to"]
                new_distance = current_distance + float(edge["weight"])
                if new_distance < distances.get(neighbor, inf):
                    distances[neighbor] = new_distance
                    previous[neighbor] = current_node
                    heapq.heappush(queue, (new_distance, neighbor))

        if distances[destination] == inf:
            raise RouteNotFoundError("No route found between origin and destination")

        path = [destination]
        while path[-1] != origin:
            path.append(previous[path[-1]])
        path.reverse()

        return {"path": path, "total_time_minutes": distances[destination]}

    @staticmethod
    def _validate_weights(graph: dict[str, list[dict]]) -> None:
        for node, edges in graph.items():
            for edge in edges:
                weight = edge.get("weight")
                if isinstance(weight, bool) or not isinstance(weight, (int, float, Decimal)):
                    raise InvalidEdgeWeightError(f"Edge from '{node}' has a non-numeric weight")

                numeric_weight = float(weight)
                if not isfinite(numeric_weight):
                    raise InvalidEdgeWeightError(f"Edge from '{node}' has a non-finite weight")
                if numeric_weight < 0:
                    raise InvalidEdgeWeightError(f"Edge from '{node}' has a negative weight")
