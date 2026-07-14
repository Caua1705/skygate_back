(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SkyGateConnections = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const DEFAULT_ESTIMATED_SECONDS_PER_VIEWBOX_UNIT = 0.25;
  const round = value => Math.round(value * 100) / 100;

  function distanceBetween(from, to) {
    return round(Math.hypot(Number(to.x) - Number(from.x), Number(to.y) - Number(from.y)));
  }

  function isDuplicate(edges, fromCode, toCode) {
    return edges.some(edge =>
      (edge.from_code === fromCode && edge.to_code === toCode) ||
      (edge.from_code === toCode && edge.to_code === fromCode)
    );
  }

  function estimatedWalkTime(viewboxDistance, factor = DEFAULT_ESTIMATED_SECONDS_PER_VIEWBOX_UNIT) {
    return round(Number(viewboxDistance) * Number(factor));
  }

  function requiredAccessibility(from, to, edgeType = "corridor") {
    const types = new Set([from?.type, to?.type, edgeType]);
    if (types.has("stairs") || types.has("escalator")) return false;
    if (types.has("elevator")) return true;
    return null;
  }

  function createEdge(graph, fromCode, toCode) {
    const from = graph.nodes.find(node => node.code === fromCode);
    const to = graph.nodes.find(node => node.code === toCode);
    if (!from || !to) return { created: false, reason: "missing_node", graph };
    if (from.code === to.code) return { created: false, reason: "same_node", graph };
    if (isDuplicate(graph.edges, from.code, to.code)) return { created: false, reason: "duplicate", graph };

    const viewboxDistance = distanceBetween(from, to);
    const factor = graph.estimated_seconds_per_viewbox_unit ?? DEFAULT_ESTIMATED_SECONDS_PER_VIEWBOX_UNIT;
    const edge = {
      from_code: from.code,
      to_code: to.code,
      edge_type: "corridor",
      viewbox_distance: viewboxDistance,
      distance_meters: null,
      walk_time_seconds: estimatedWalkTime(viewboxDistance, factor),
      instruction: null,
      is_bidirectional: true,
      is_accessible: requiredAccessibility(from, to) ?? true,
      is_estimated: true,
    };
    return { created: true, edge, graph: { ...graph, edges: [...graph.edges, edge] } };
  }

  return {
    DEFAULT_ESTIMATED_SECONDS_PER_VIEWBOX_UNIT,
    distanceBetween,
    estimatedWalkTime,
    requiredAccessibility,
    isDuplicate,
    createEdge,
  };
});
