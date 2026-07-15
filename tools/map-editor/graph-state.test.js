const test = require("node:test");
const assert = require("node:assert/strict");
const {
  findOrphanEdges,
  removeOrphanEdges,
  removeNodeAndIncidentEdges,
  renameNodeCode,
  backupStoredGraph,
} = require("./graph-state.js");

const graph = () => ({
  airport: { slug: "fortaleza" },
  nodes: [
    { id: "a-id", code: "a", name: "A", floor: "0", x: 10, y: 20 },
    { id: "b-id", code: "b", name: "B", floor: "1", x: 30, y: 40 },
    { id: "c-id", code: "c", name: "C", floor: "1", x: 50, y: 60 },
  ],
  edges: [
    { from_code: "a", to_code: "b", edge_type: "elevator", instruction: "subir" },
    { from_code: "b", to_code: "c", edge_type: "corridor", instruction: "seguir" },
  ],
  businesses: [{ node_code: "a", name: "Café" }],
});

test("excluir nó remove somente suas arestas de origem ou destino", () => {
  const original = graph();
  const result = removeNodeAndIncidentEdges(original, "a-id");
  assert.equal(result.removedCount, 1);
  assert.deepEqual(result.graph.nodes, original.nodes.slice(1));
  assert.deepEqual(result.graph.edges, [original.edges[1]]);
  assert.deepEqual(result.graph.businesses, original.businesses);
});

test("renomear código atualiza origem e destino sem alterar os demais dados", () => {
  const original = graph();
  original.edges.push({ from_code: "c", to_code: "a", edge_type: "corridor", instruction: "voltar" });
  const result = renameNodeCode(original, "a-id", "entrada");
  assert.equal(result.renamed, true);
  assert.deepEqual(result.graph.nodes[0], { ...original.nodes[0], code: "entrada" });
  assert.deepEqual(result.graph.edges[0], { ...original.edges[0], from_code: "entrada" });
  assert.deepEqual(result.graph.edges[2], { ...original.edges[2], to_code: "entrada" });
  assert.deepEqual(result.graph.edges[1], original.edges[1]);
});

test("limpeza remove apenas arestas órfãs e preserva nós e conexões válidas", () => {
  const original = graph();
  original.edges.push(
    { from_code: "a", to_code: "ausente", edge_type: "corridor" },
    { from_code: "fantasma", to_code: "b", edge_type: "corridor" }
  );
  assert.equal(findOrphanEdges(original).length, 2);
  const result = removeOrphanEdges(original);
  assert.equal(result.removedCount, 2);
  assert.deepEqual(result.graph.nodes, original.nodes);
  assert.deepEqual(result.graph.edges, original.edges.slice(0, 2));
  assert.deepEqual(result.graph.businesses, original.businesses);
});

test("backup preserva exatamente o estado armazenado antes da limpeza", () => {
  const values = new Map([["graph", "{\"estado\":\"antes\"}"]]);
  const storage = {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, value),
  };
  backupStoredGraph(storage, "graph", "backup", graph());
  assert.equal(values.get("backup"), "{\"estado\":\"antes\"}");
  assert.equal(values.get("graph"), "{\"estado\":\"antes\"}");
});
