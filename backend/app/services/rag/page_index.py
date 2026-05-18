"""Vectorless RAG via PageIndex: hierarchical tree of (page → section → row).
No embeddings — pure traversal + keyword matching, super fast on CPU.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.config import settings


@dataclass
class PageNode:
    page_id: int
    title: str
    summary: str
    children: List["PageNode"] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "summary": self.summary,
            "data": self.data,
            "children": [c.to_dict() for c in self.children],
        }


class PageIndex:
    """In-memory hierarchical index persisted as JSON per document."""

    def __init__(self):
        self.dir = Path(settings.graph_dir) / "pageindex"
        self.dir.mkdir(parents=True, exist_ok=True)

    def save_document_tree(self, document_id: int, tree: PageNode) -> None:
        (self.dir / f"{document_id}.json").write_text(json.dumps(tree.to_dict(), default=str))

    def load_document_tree(self, document_id: int) -> Optional[Dict[str, Any]]:
        p = self.dir / f"{document_id}.json"
        if not p.exists():
            return None
        return json.loads(p.read_text())

    def all_trees(self) -> List[Dict[str, Any]]:
        return [json.loads(p.read_text()) for p in self.dir.glob("*.json")]

    @staticmethod
    def build_from_records(document_id: int, title: str, records: List[Dict[str, Any]]) -> PageNode:
        root = PageNode(page_id=document_id, title=title or "Document",
                        summary=f"{len(records)} records")
        for r in records:
            label = f"Row {r.get('row_index')}: {r.get('machine_no','?')} / {r.get('employee_no','?')}"
            summ = " | ".join(f"{k}={r.get(k)}" for k in
                              ["date", "shift", "work_order_no", "quantity_produced", "time_taken_hours"]
                              if r.get(k) is not None)
            root.children.append(PageNode(page_id=document_id, title=label, summary=summ, data=r))
        return root

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        q = query.lower()
        terms = [t for t in re.split(r"\W+", q) if t]
        hits: List[Dict[str, Any]] = []
        for tree in self.all_trees():
            for child in tree.get("children", []):
                blob = f"{child.get('title','')} {child.get('summary','')}".lower()
                score = sum(blob.count(t) for t in terms)
                if score > 0:
                    hits.append({"score": score, "document_id": tree["page_id"],
                                 "title": child["title"], "summary": child["summary"],
                                 "data": child.get("data")})
        hits.sort(key=lambda x: -x["score"])
        return hits[:top_k]


page_index = PageIndex()
