"""GraphRAG with NetworkX persisted as JSON. Tiny, CPU-friendly, no DB."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx

from ...core.config import settings


class GraphRAG:
    def __init__(self):
        self.path = Path(settings.graph_dir) / "graph.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.g: nx.MultiDiGraph = self._load()

    def _load(self) -> nx.MultiDiGraph:
        if not self.path.exists():
            return nx.MultiDiGraph()
        try:
            data = json.loads(self.path.read_text())
            return nx.node_link_graph(data, multigraph=True, directed=True)
        except Exception:
            return nx.MultiDiGraph()

    def save(self):
        data = nx.node_link_data(self.g)
        self.path.write_text(json.dumps(data, default=str))

    def add_record_triples(self, document_id: int, record_id: int, rec: Dict[str, Any]):
        machine = rec.get("machine_no")
        emp = rec.get("employee_no")
        wo = f"WO-{rec.get('work_order_no')}" if rec.get("work_order_no") else None
        meta = {"document_id": document_id, "record_id": record_id}
        if machine and emp:
            self.g.add_edge(machine, emp, key="operated_by", **meta)
        if emp and wo:
            self.g.add_edge(emp, wo, key="worked_on", **meta)
        if wo:
            if rec.get("quantity_produced") is not None:
                self.g.add_edge(wo, f"qty:{rec['quantity_produced']}", key="produced", value=rec["quantity_produced"], **meta)
            if rec.get("time_taken_hours") is not None:
                self.g.add_edge(wo, f"hrs:{rec['time_taken_hours']}", key="took_time", value=rec["time_taken_hours"], **meta)
            if rec.get("shift"):
                self.g.add_edge(wo, f"shift:{rec['shift']}", key="assigned_shift", **meta)
            if rec.get("date"):
                self.g.add_edge(wo, f"date:{rec['date']}", key="executed_on", **meta)
            if rec.get("operation_code"):
                self.g.add_edge(wo, f"op:{rec['operation_code']}", key="uses_operation", **meta)

    def neighbors(self, node: str, depth: int = 1) -> List[Dict[str, Any]]:
        if node not in self.g:
            return []
        seen = {node}
        frontier = [node]
        result = []
        for _ in range(depth):
            nxt = []
            for n in frontier:
                for _, t, k, d in self.g.out_edges(n, keys=True, data=True):
                    if t in seen:
                        continue
                    seen.add(t)
                    nxt.append(t)
                    result.append({"source": n, "target": t, "predicate": k, "meta": d})
            frontier = nxt
        return result

    def query(self, terms: List[str], depth: int = 2) -> List[Dict[str, Any]]:
        # Find any node containing the term, then walk
        results = []
        for n in list(self.g.nodes()):
            ns = str(n).lower()
            if any(t.lower() in ns for t in terms):
                results.append({"node": n, "edges": self.neighbors(n, depth)})
        return results


graph_rag = GraphRAG()
