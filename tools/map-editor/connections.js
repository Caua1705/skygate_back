(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SkyGateConnections = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

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

  function createEdge(graph, fromCode, toCode) {
    const from = graph.nodes.find(node => node.code === fromCode);
    const to = graph.nodes.find(node => node.code === toCode);
    if (!from || !to) return { created: false, reason: "missing_node", graph };
    if (from.code === to.code) return { created: false, reason: "same_node", graph };
    if (isDuplicate(graph.edges, from.code, to.code)) return { created: false, reason: "duplicate", graph };

    const distance = distanceBetween(from, to);
    const edge = {
      from_code: from.code,
      to_code: to.code,
      edge_type: "corridor",
      distance_meters: distance,
      walk_time_seconds: distance,
      instruction: null,
      is_bidirectional: true,
      is_accessible: true,
      is_estimated: true,
    };
    return { created: true, edge, graph: { ...graph, edges: [...graph.edges, edge] } };
  }

  return { distanceBetween, isDuplicate, createEdge };
});
