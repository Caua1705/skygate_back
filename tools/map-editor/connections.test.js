const test = require("node:test");
const assert = require("node:assert/strict");
const { createEdge, distanceBetween } = require("./connections.js");

const graph = () => ({
  airport: { slug: "fortaleza" },
  nodes: [
    { id: "a-id", code: "a", name: "A", floor: "0", x: 0, y: 0 },
    { id: "b-id", code: "b", name: "B", floor: "0", x: 3, y: 4 },
    { id: "c-id", code: "c", name: "C", floor: "0", x: 6, y: 8 },
  ],
  edges: [], businesses: [],
});

test("calcula a distância entre as coordenadas dos nós", () => {
  assert.equal(distanceBetween(graph().nodes[0], graph().nodes[1]), 5);
});

test("cria somente uma aresta bidirecional com os padrões esperados", () => {
  const original = graph();
  const result = createEdge(original, "a", "b");
  assert.equal(result.created, true);
  assert.equal(result.graph.nodes.length, original.nodes.length);
  assert.deepEqual(result.graph.nodes, original.nodes);
  assert.equal(result.graph.edges.length, 1);
  assert.deepEqual(result.edge, {
    from_code: "a", to_code: "b", edge_type: "corridor", distance_meters: 5,
    walk_time_seconds: 5, instruction: null, is_bidirectional: true,
    is_accessible: true, is_estimated: true,
  });
});

test("permite conexões consecutivas sem criar nós", () => {
  const original = graph();
  const first = createEdge(original, "a", "b");
  const second = createEdge(first.graph, "b", "c");
  assert.equal(second.graph.edges.length, 2);
  assert.deepEqual(second.graph.nodes, original.nodes);
});

test("não cria conexão duplicada em nenhum sentido", () => {
  const first = createEdge(graph(), "a", "b");
  first.graph.edges[0].is_bidirectional = false;
  const duplicate = createEdge(first.graph, "b", "a");
  assert.equal(duplicate.created, false);
  assert.equal(duplicate.reason, "duplicate");
  assert.equal(duplicate.graph.edges.length, 1);
});
