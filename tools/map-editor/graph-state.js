(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SkyGateGraphState = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function findOrphanEdges(graph) {
    const codes = new Set((graph.nodes || []).map(node => node.code));
    return (graph.edges || []).filter(edge => !codes.has(edge.from_code) || !codes.has(edge.to_code));
  }

  function removeOrphanEdges(graph) {
    const removedEdges = findOrphanEdges(graph);
    const orphans = new Set(removedEdges);
    return {
      graph: { ...graph, edges: (graph.edges || []).filter(edge => !orphans.has(edge)) },
      removedEdges,
      removedCount: removedEdges.length,
    };
  }

  function removeNodeAndIncidentEdges(graph, nodeId) {
    const node = (graph.nodes || []).find(item => item.id === nodeId);
    if (!node) return { graph, removedEdges: [], removedCount: 0 };
    const removedEdges = (graph.edges || []).filter(edge => edge.from_code === node.code || edge.to_code === node.code);
    const removed = new Set(removedEdges);
    return {
      graph: {
        ...graph,
        nodes: graph.nodes.filter(item => item.id !== nodeId),
        edges: graph.edges.filter(edge => !removed.has(edge)),
      },
      removedEdges,
      removedCount: removedEdges.length,
    };
  }

  function renameNodeCode(graph, nodeId, nextCode) {
    const node = (graph.nodes || []).find(item => item.id === nodeId);
    if (!node || node.code === nextCode) return { graph, renamed: false };
    const previousCode = node.code;
    return {
      graph: {
        ...graph,
        nodes: graph.nodes.map(item => item.id === nodeId ? { ...item, code: nextCode } : item),
        edges: graph.edges.map(edge => ({
          ...edge,
          from_code: edge.from_code === previousCode ? nextCode : edge.from_code,
          to_code: edge.to_code === previousCode ? nextCode : edge.to_code,
        })),
      },
      renamed: true,
      previousCode,
    };
  }

  function backupStoredGraph(storage, storageKey, backupKey, fallbackGraph) {
    const stored = storage.getItem(storageKey);
    storage.setItem(backupKey, stored === null ? JSON.stringify(fallbackGraph) : stored);
  }

  return { findOrphanEdges, removeOrphanEdges, removeNodeAndIncidentEdges, renameNodeCode, backupStoredGraph };
});
