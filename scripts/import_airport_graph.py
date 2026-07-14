"""Valida e importa um grafo exportado pelo editor SkyGate.

Uso: python scripts/import_airport_graph.py data/airports/fortaleza/graph_v1.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import SessionLocal
from src.models.airport_business_model import AirportBusiness
from src.models.airport_edge_model import AirportEdge
from src.models.airport_node_model import AirportNode
from src.repositories.airport_repository import AirportRepository

ZONES = {"public", "checkin", "security", "domestic_airside", "international_airside", "connection", "baggage_claim", "restricted"}
EDGE_TYPES = {"corridor", "ramp", "stairs", "escalator", "elevator", "security", "boarding", "restricted_transition"}
CONNECTOR_TYPES = {"elevator", "stairs", "escalator"}
INACCESSIBLE_CONNECTOR_TYPES = {"stairs", "escalator"}
TWO_DECIMAL_PLACES = Decimal("0.01")


class GraphValidationError(ValueError):
    """Raised before any database write when an export cannot be safely imported."""


@dataclass
class Counts:
    inserted: Counter = field(default_factory=Counter)
    updated: Counter = field(default_factory=Counter)
    ignored: Counter = field(default_factory=Counter)

    def show(self) -> str:
        labels = ("nodes", "edges", "businesses")
        return "\n".join(f"{label}: inserir={self.inserted[label]}, atualizar={self.updated[label]}, ignorar={self.ignored[label]}" for label in labels)


def decimal(value: Any, label: str, *, required: bool = False) -> Decimal | None:
    if value is None or value == "":
        if required:
            raise GraphValidationError(f"{label} é obrigatório")
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise GraphValidationError(f"{label} deve ser numérico") from exc
    if not result.is_finite() or result < 0:
        raise GraphValidationError(f"{label} deve ser finito e não negativo")
    return result


def rounded(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def euclidean_viewbox_distance(source: dict[str, Any], target: dict[str, Any]) -> Decimal:
    dx = decimal(target["x"], "x", required=True) - decimal(source["x"], "x", required=True)
    dy = decimal(target["y"], "y", required=True) - decimal(source["y"], "y", required=True)
    return rounded((dx * dx + dy * dy).sqrt())


def required_accessibility(source: dict[str, Any], target: dict[str, Any], edge_type: str) -> bool | None:
    types = {source.get("type"), target.get("type"), edge_type}
    if types & INACCESSIBLE_CONNECTOR_TYPES:
        return False
    if "elevator" in types:
        return True
    return None


def validate_graph(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or set(("airport", "nodes", "edges", "businesses")) - data.keys():
        raise GraphValidationError("JSON deve conter airport, nodes, edges e businesses")
    airport = data["airport"]
    if not isinstance(airport, dict) or not isinstance(airport.get("slug"), str) or not airport["slug"].strip():
        raise GraphValidationError("airport.slug é obrigatório")
    for key in ("nodes", "edges", "businesses"):
        if not isinstance(data[key], list):
            raise GraphValidationError(f"{key} deve ser uma lista")
    factor = decimal(data.get("estimated_seconds_per_viewbox_unit"), "estimated_seconds_per_viewbox_unit", required=True)
    if factor == 0:
        raise GraphValidationError("estimated_seconds_per_viewbox_unit deve ser maior que zero")
    estimation = data.get("time_estimation")
    if not isinstance(estimation, dict) or estimation.get("is_estimated") is not True or estimation.get("validated_on_site") is not False:
        raise GraphValidationError("time_estimation deve informar estimativa não validada presencialmente")
    codes: set[str] = set()
    nodes: dict[str, dict[str, Any]] = {}
    for item in data["nodes"]:
        if not isinstance(item, dict): raise GraphValidationError("cada nó deve ser um objeto")
        code = item.get("code")
        if not isinstance(code, str) or not code.strip() or code in codes: raise GraphValidationError(f"código de nó inválido/duplicado: {code!r}")
        if not isinstance(item.get("name"), str) or not item["name"].strip() or not isinstance(item.get("type"), str) or not item["type"].strip(): raise GraphValidationError(f"nó {code}: name e type são obrigatórios")
        if str(item.get("floor")) not in {"0", "1", "2", "3"}: raise GraphValidationError(f"nó {code}: floor deve estar entre 0 e 3")
        if item.get("zone", "public") not in ZONES: raise GraphValidationError(f"nó {code}: zone inválida")
        for axis in ("x", "y"): decimal(item.get(axis), f"nó {code}.{axis}", required=True)
        codes.add(code); nodes[code] = item
    pairs: set[tuple[str, str]] = set()
    for edge in data["edges"]:
        if not isinstance(edge, dict): raise GraphValidationError("cada aresta deve ser um objeto")
        pair = (edge.get("from_code"), edge.get("to_code"))
        if not all(isinstance(code, str) and code in nodes for code in pair) or pair[0] == pair[1]: raise GraphValidationError(f"aresta com nós inválidos: {pair}")
        if pair in pairs: raise GraphValidationError(f"aresta duplicada: {pair[0]} -> {pair[1]}")
        if edge.get("edge_type", "corridor") not in EDGE_TYPES: raise GraphValidationError(f"aresta {pair}: edge_type inválido")
        if nodes[pair[0]]["floor"] != nodes[pair[1]]["floor"] and edge.get("edge_type") not in CONNECTOR_TYPES: raise GraphValidationError(f"aresta {pair}: troca de piso exige elevador, escada ou escada rolante")
        viewbox_distance = decimal(edge.get("viewbox_distance"), f"aresta {pair}.viewbox_distance", required=True)
        expected_viewbox_distance = euclidean_viewbox_distance(nodes[pair[0]], nodes[pair[1]])
        if viewbox_distance != expected_viewbox_distance:
            raise GraphValidationError(f"aresta {pair}: viewbox_distance deve ser {expected_viewbox_distance}")
        if "distance_meters" not in edge or edge["distance_meters"] is not None:
            raise GraphValidationError(f"aresta {pair}.distance_meters deve ser null")
        walk_time = decimal(edge.get("walk_time_seconds"), f"aresta {pair}.walk_time_seconds", required=True)
        expected_walk_time = rounded(viewbox_distance * factor)
        if walk_time != expected_walk_time:
            raise GraphValidationError(f"aresta {pair}: walk_time_seconds deve ser {expected_walk_time}")
        if edge.get("is_estimated") is not True:
            raise GraphValidationError(f"aresta {pair}.is_estimated deve permanecer true")
        required_accessible = required_accessibility(nodes[pair[0]], nodes[pair[1]], edge.get("edge_type", "corridor"))
        if required_accessible is not None and edge.get("is_accessible") is not required_accessible:
            expected = "true" if required_accessible else "false"
            raise GraphValidationError(f"aresta {pair}.is_accessible deve ser {expected}")
        pairs.add(pair)
    for business in data["businesses"]:
        if not isinstance(business, dict) or business.get("node_code") not in nodes: raise GraphValidationError("business.node_code deve referenciar um nó")
        if not isinstance(business.get("name"), str) or not business["name"].strip() or not isinstance(business.get("category"), str) or not business["category"].strip(): raise GraphValidationError("business.name e category são obrigatórios")
    return data


def _apply(model: Any, values: dict[str, Any]) -> bool:
    """Apply only changed attributes and report whether this is an update."""
    changed = False
    for key, value in values.items():
        if getattr(model, key) != value:
            setattr(model, key, value)
            changed = True
    return changed


def import_graph(session: Session, data: dict[str, Any], *, dry_run: bool = False) -> Counts:
    data = validate_graph(data); airport = AirportRepository(session).get_by_slug(data["airport"]["slug"])
    if airport is None: raise GraphValidationError(f"Aeroporto não encontrado: {data['airport']['slug']}")
    counts = Counts(); existing_nodes = {node.code: node for node in session.scalars(select(AirportNode).where(AirportNode.airport_id == airport.id))}
    node_by_code: dict[str, AirportNode] = {}
    for row in data["nodes"]:
        values = {"name":row["name"].strip(),"type":row["type"].strip(),"floor":str(row["floor"]),"x":decimal(row["x"],"x",required=True),"y":decimal(row["y"],"y",required=True),"zone":row.get("zone","public"),"connector_group":row.get("connector_group") or None,"is_accessible":bool(row.get("is_accessible",True)),"is_restricted":bool(row.get("is_restricted",False)),"is_estimated":bool(row.get("is_estimated",False))}
        node = existing_nodes.get(row["code"])
        if node is None: node = AirportNode(airport_id=airport.id, code=row["code"], **values); session.add(node); counts.inserted["nodes"] += 1
        elif _apply(node, values): counts.updated["nodes"] += 1
        else: counts.ignored["nodes"] += 1
        node_by_code[row["code"]] = node
    session.flush()
    existing_edges = {(str(e.from_node_id),str(e.to_node_id)):e for e in session.scalars(select(AirportEdge).where(AirportEdge.airport_id == airport.id))}
    for row in data["edges"]:
        source,target=node_by_code[row["from_code"]],node_by_code[row["to_code"]]; values={"walk_time_minutes":decimal(row["walk_time_seconds"],"seconds",required=True)/Decimal(60),"distance_meters":decimal(row.get("distance_meters"),"distance"),"instruction":row.get("instruction") or None,"edge_type":row.get("edge_type","corridor"),"is_bidirectional":bool(row.get("is_bidirectional",False)),"is_accessible":bool(row.get("is_accessible",True)),"is_estimated":bool(row.get("is_estimated",False))}; key=(str(source.id),str(target.id)); edge=existing_edges.get(key)
        if edge is None: session.add(AirportEdge(airport_id=airport.id,from_node_id=source.id,to_node_id=target.id,**values)); counts.inserted["edges"] += 1
        elif _apply(edge,values): counts.updated["edges"] += 1
        else: counts.ignored["edges"] += 1
    session.flush()
    for row in data["businesses"]:
        node=node_by_code[row["node_code"]]
        query=select(AirportBusiness).where(AirportBusiness.airport_id==airport.id)
        if row.get("external_id"):
            query=query.where(AirportBusiness.external_id==row["external_id"])
        else:
            query=query.where(AirportBusiness.node_id==node.id,AirportBusiness.name==row["name"])
        business=session.scalar(query); values={"category":row["category"],"description":row.get("description"),"estimated_stop_minutes":decimal(row.get("estimated_stop_minutes",0),"estimated_stop_minutes") or Decimal(0),"is_active":bool(row.get("is_active",True)),"external_id":row.get("external_id"),"floor":str(row.get("floor",node.floor)) if row.get("floor",node.floor) is not None else None,"x":decimal(row.get("x"),"business.x"),"y":decimal(row.get("y"),"business.y"),"location_is_estimated":bool(row.get("location_is_estimated",False))}
        if business is None: session.add(AirportBusiness(airport_id=airport.id,node_id=node.id,name=row["name"],**values)); counts.inserted["businesses"] += 1
        elif _apply(business,{**values, "node_id": node.id}): counts.updated["businesses"] += 1
        else: counts.ignored["businesses"] += 1
    if dry_run: session.rollback()
    return counts


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("json_path",type=Path); parser.add_argument("--dry-run",action="store_true"); args=parser.parse_args()
    try:
        data=json.loads(args.json_path.read_text(encoding="utf-8")); validate_graph(data)
        with SessionLocal() as session:
            with session.begin(): counts=import_graph(session,data,dry_run=args.dry_run)
        print(("Simulação concluída.\n" if args.dry_run else "Importação concluída.\n") + counts.show()); return 0
    except (OSError,json.JSONDecodeError,GraphValidationError) as exc: print(f"Erro: {exc}",file=sys.stderr); return 2
    except Exception as exc: print(f"Erro: transação revertida: {exc}",file=sys.stderr); return 1

if __name__ == "__main__": raise SystemExit(main())
