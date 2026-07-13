/* Editor local: coordenadas são sempre convertidas para o viewBox do SVG. */
const MAPS = Object.fromEntries([0, 1, 2, 3].map(n => [n, `../../data/airports/fortaleza/maps/fortaleza_piso_${n}.svg`]));
const STORAGE = "skygate:fortaleza:graph:v1";
const empty = () => ({ airport: { slug: "fortaleza", name: "Aeroporto de Fortaleza" }, nodes: [], edges: [], businesses: [] });
let graph = load(), floor = 0, selectedNode = null, selectedEdge = null, svg, baseViewBox, drag;
const $ = selector => document.querySelector(selector);
function load() { try { return JSON.parse(localStorage.getItem(STORAGE)) || empty(); } catch { return empty(); } }
function save() { localStorage.setItem(STORAGE, JSON.stringify(graph)); render(); }
function uid() { return crypto.randomUUID ? crypto.randomUUID() : `n-${Date.now()}-${Math.random()}`; }
function num(value) { return value === "" || value == null ? null : Number(value); }
function checked(form, name) { return form.elements[name].checked; }
function setTabs() { document.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => { document.querySelectorAll("[data-tab],.panel").forEach(x => x.classList.remove("active")); b.classList.add("active"); $(`#${b.dataset.tab}`).classList.add("active"); }); }

async function showFloor(next) {
  floor = Number(next); selectedNode = selectedEdge = null;
  const text = await fetch(MAPS[floor]).then(r => r.text());
  const doc = new DOMParser().parseFromString(text, "image/svg+xml");
  svg = document.importNode(doc.documentElement, true); svg.removeAttribute("width"); svg.removeAttribute("height");
  if (!svg.viewBox.baseVal.width) svg.setAttribute("viewBox", "0 0 1000 1000");
  baseViewBox = { ...svg.viewBox.baseVal };
  svg.insertAdjacentHTML("beforeend", '<defs><marker id="sgArrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z"/></marker></defs><g id="sgEdges"></g><g id="sgNodes"></g>');
  $("#map").replaceChildren(svg); bindMap(); render();
}
function bindMap() {
  svg.addEventListener("click", event => { if (event.target.closest(".node,.edge")) return; const p = point(event); selectedNode = { id: uid(), code:"", name:"", type:"waypoint", floor:String(floor), x:round(p.x), y:round(p.y), zone:"public", is_accessible:true, is_restricted:false }; selectedEdge = null; fillNode(); render(); });
  svg.addEventListener("wheel", event => { event.preventDefault(); zoom(event.deltaY > 0 ? 1.15 : .87, point(event)); }, { passive:false });
  svg.addEventListener("pointerdown", e => { if (!e.target.closest(".node,.edge")) { drag = { x:e.clientX, y:e.clientY, box:{...svg.viewBox.baseVal} }; svg.setPointerCapture(e.pointerId); } });
  svg.addEventListener("pointermove", e => { if (!drag) return; const r=svg.getBoundingClientRect(), b=svg.viewBox.baseVal; b.x=drag.box.x-(e.clientX-drag.x)*drag.box.width/r.width; b.y=drag.box.y-(e.clientY-drag.y)*drag.box.height/r.height; });
  svg.addEventListener("pointerup", () => drag=null);
}
function point(e) { const p=svg.createSVGPoint(); p.x=e.clientX; p.y=e.clientY; return p.matrixTransform(svg.getScreenCTM().inverse()); }
function round(n) { return Math.round(n * 100) / 100; }
function zoom(factor, center) { const b=svg.viewBox.baseVal; b.x=center.x-(center.x-b.x)*factor; b.y=center.y-(center.y-b.y)*factor; b.width*=factor; b.height*=factor; }
function fit() { const b=svg.viewBox.baseVal; Object.assign(b, { x:baseViewBox.x, y:baseViewBox.y, width:baseViewBox.width, height:baseViewBox.height }); }
function render() {
  if (!svg) return; $("#floors").replaceChildren(...[0,1,2,3].map(n => { const b=document.createElement("button"); b.textContent=`Piso ${n}`; b.className=n===floor?"active":""; b.onclick=()=>showFloor(n); return b; }));
  const nodes = graph.nodes.filter(n => String(n.floor) === String(floor)), byCode=Object.fromEntries(graph.nodes.map(n=>[n.code,n]));
  const edges = $("#sgEdges"); edges.replaceChildren(); graph.edges.forEach((e, i) => { const a=byCode[e.from_code], b=byCode[e.to_code]; if (!a || !b || (String(a.floor)!==String(floor) && String(b.floor)!==String(floor))) return; const line=document.createElementNS(svg.namespaceURI,"line"); line.setAttribute("x1",a.x);line.setAttribute("y1",a.y);line.setAttribute("x2",b.x);line.setAttribute("y2",b.y);line.classList.add("edge"); if (selectedEdge===i) line.classList.add("selected"); if (!e.is_bidirectional) line.setAttribute("marker-end","url(#sgArrow)"); line.onclick=()=>{selectedEdge=i;selectedNode=null;fillEdge();render();}; edges.append(line); });
  const layer=$("#sgNodes"); layer.replaceChildren(); nodes.forEach(n=>{ const c=document.createElementNS(svg.namespaceURI,"circle"); c.setAttribute("cx",n.x);c.setAttribute("cy",n.y);c.setAttribute("r",Math.max(svg.viewBox.baseVal.width,svg.viewBox.baseVal.height)/130);c.classList.add("node"); if (selectedNode?.id===n.id) c.classList.add("selected"); c.onclick=()=>{selectedNode=n;selectedEdge=null;fillNode();render();}; const title=document.createElementNS(svg.namespaceURI,"title");title.textContent=`${n.code} — ${n.name}`;c.append(title);layer.append(c); });
  fillSelects();
}
function fillSelects() { const options=graph.nodes.map(n=>`<option value="${escape(n.code)}">${escape(n.code)} — ${escape(n.name)}</option>`).join(""); ["from_code","to_code"].forEach(n=>{ const v=$("#edgeForm").elements[n].value; $("#edgeForm").elements[n].innerHTML=options; $("#edgeForm").elements[n].value=v; }); ["#routeFrom", "#routeTo"].forEach(s=>{const old=$(s).value; $(s).innerHTML=options; $(s).value=old;}); }
function escape(v) { return String(v??"").replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function fillNode() { const f=$("#nodeForm"); if(!selectedNode) { f.reset(); $("#coordinates").textContent="Clique no mapa para definir coordenadas."; return; } Object.entries(selectedNode).forEach(([k,v])=>{ if(f.elements[k]) f.elements[k].type==="checkbox" ? f.elements[k].checked=!!v : f.elements[k].value=v??""; }); $("#coordinates").textContent=`viewBox: x ${selectedNode.x}, y ${selectedNode.y}`; }
function fillEdge() { const f=$("#edgeForm"); if(selectedEdge==null) { f.reset(); f.elements.walk_time_seconds.value=0; return; } const e=graph.edges[selectedEdge]; Object.entries(e).forEach(([k,v])=>{if(f.elements[k]) f.elements[k].type==="checkbox"?f.elements[k].checked=!!v:f.elements[k].value=v??"";}); }
function validate(g=graph) { const errors=[], codes=new Set(), nodes=Object.fromEntries(g.nodes.map(n=>[n.code,n])), pairs=new Set(), linked=new Set(); for(const n of g.nodes){ if(!n.code||codes.has(n.code)) errors.push(`Código duplicado ou vazio: ${n.code||"(vazio)"}`); codes.add(n.code); if(!Number.isFinite(n.x)||!Number.isFinite(n.y)) errors.push(`Coordenadas inválidas: ${n.code}`); } for(const e of g.edges){ const key=`${e.from_code}>${e.to_code}`; if(pairs.has(key)) errors.push(`Aresta duplicada: ${key}`); pairs.add(key); const a=nodes[e.from_code],b=nodes[e.to_code]; if(!a||!b) errors.push(`Aresta aponta para nó inexistente: ${key}`); else { linked.add(a.code);linked.add(b.code); if(a.floor!==b.floor && !["elevator","stairs","escalator"].includes(e.edge_type)) errors.push(`Mudança de piso inválida: ${key}`); } if(!Number.isFinite(e.walk_time_seconds)||e.walk_time_seconds<0||(e.distance_meters!=null&&(!Number.isFinite(e.distance_meters)||e.distance_meters<0))) errors.push(`Peso inválido: ${key}`); } g.nodes.filter(n=>!linked.has(n.code)).forEach(n=>errors.push(`Nó isolado: ${n.code}`)); return errors; }
function dijkstra(accessible) { const from=$("#routeFrom").value,to=$("#routeTo").value, dist=Object.fromEntries(graph.nodes.map(n=>[n.code,Infinity])), prev={}; dist[from]=0; const done=new Set(); while(true){const cur=Object.keys(dist).filter(k=>!done.has(k)).sort((a,b)=>dist[a]-dist[b])[0];if(!cur||dist[cur]===Infinity)break;if(cur===to)break;done.add(cur);for(const e of graph.edges){for(const [a,b] of e.is_bidirectional?[[e.from_code,e.to_code],[e.to_code,e.from_code]]:[[e.from_code,e.to_code]]){const na=graph.nodes.find(n=>n.code===a),nb=graph.nodes.find(n=>n.code===b);if(a!==cur|| (accessible && (!e.is_accessible||!na?.is_accessible||!nb?.is_accessible||na?.is_restricted||nb?.is_restricted||e.edge_type==="stairs")))continue;const next=dist[cur]+e.walk_time_seconds;if(next<dist[b]){dist[b]=next;prev[b]=cur;}}}} if(dist[to]===Infinity)return "Sem rota disponível."; const path=[];for(let x=to;x;x=prev[x])path.unshift(x);return `${path.join(" → ")}\n${dist[to]} segundos`; }
$("#nodeForm").onsubmit=e=>{e.preventDefault();if(!selectedNode)return;const f=e.currentTarget,n={...selectedNode};["code","name","type","floor","zone","connector_group"].forEach(k=>n[k]=f.elements[k].value.trim()||null);["is_accessible","is_restricted"].forEach(k=>n[k]=checked(f,k));if(!n.code||!n.name||graph.nodes.some(x=>x.code===n.code&&x.id!==n.id)){alert("Código e nome são obrigatórios; o código deve ser único.");return;}const i=graph.nodes.findIndex(x=>x.id===n.id);if(i<0)graph.nodes.push(n);else graph.nodes[i]=n;selectedNode=n;save();};
$("#deleteNode").onclick=()=>{if(!selectedNode)return;graph.nodes=graph.nodes.filter(n=>n.id!==selectedNode.id);graph.edges=graph.edges.filter(e=>e.from_code!==selectedNode.code&&e.to_code!==selectedNode.code);selectedNode=null;save();};
$("#edgeForm").onsubmit=e=>{e.preventDefault();const f=e.currentTarget,n={from_code:f.from_code.value,to_code:f.to_code.value,edge_type:f.edge_type.value,distance_meters:num(f.distance_meters.value),walk_time_seconds:num(f.walk_time_seconds.value),instruction:f.instruction.value.trim()||null,is_bidirectional:checked(f,"is_bidirectional"),is_accessible:checked(f,"is_accessible"),is_estimated:checked(f,"is_estimated")};if(n.from_code===n.to_code||validate({...graph,edges:[n]}).some(x=>x.includes("Mudança")||x.includes("Peso"))){alert("Aresta inválida.");return;}if(selectedEdge==null)graph.edges.push(n);else graph.edges[selectedEdge]=n;save();};
$("#deleteEdge").onclick=()=>{if(selectedEdge==null)return;graph.edges.splice(selectedEdge,1);selectedEdge=null;save();};
$("#normalRoute").onclick=()=>$("#routeResult").textContent=dijkstra(false); $("#accessibleRoute").onclick=()=>$("#routeResult").textContent=dijkstra(true);
$("#validate").onclick=()=>{const e=validate();$("#validation").textContent=e.length?e.join("\n"):"Grafo válido.";};
$("#export").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(graph,null,2)],{type:"application/json"}));a.download="graph_v1.json";a.click();URL.revokeObjectURL(a.href);};
$("#import").onchange=async e=>{try{const g=JSON.parse(await e.target.files[0].text());if(!g.airport||!Array.isArray(g.nodes)||!Array.isArray(g.edges)||!Array.isArray(g.businesses))throw Error("Formato inválido");graph=g;selectedNode=selectedEdge=null;save();}catch(err){alert(`Importação falhou: ${err.message}`)}};
$("#clear").onclick=()=>{if(confirm("Limpar o grafo local?")){graph=empty();selectedNode=selectedEdge=null;save();}}; $("#zoomIn").onclick=()=>zoom(.8,{x:svg.viewBox.baseVal.x+svg.viewBox.baseVal.width/2,y:svg.viewBox.baseVal.y+svg.viewBox.baseVal.height/2}); $("#zoomOut").onclick=()=>zoom(1.25,{x:svg.viewBox.baseVal.x+svg.viewBox.baseVal.width/2,y:svg.viewBox.baseVal.y+svg.viewBox.baseVal.height/2}); $("#fit").onclick=fit;
setTabs(); showFloor(0);
