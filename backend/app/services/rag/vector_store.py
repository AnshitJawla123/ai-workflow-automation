"""Embedded vector store using ChromaDB + local MiniLM embeddings (CPU)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ...core.config import settings

log = logging.getLogger("rag.vector")


class VectorStore:
    def __init__(self):
        self._client = None
        self._collection = None
        self._embedder = None

    def _ensure(self):
        if self._collection is not None:
            return
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.PersistentClient(
                path=settings.chroma_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection("records")
        except Exception as e:
            log.warning("Chroma unavailable: %s", e)
            self._collection = None

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(settings.embed_model)
            except Exception as e:
                log.warning("Embedder unavailable: %s", e)
                self._embedder = False  # disable
        if not self._embedder:
            return [[0.0] * 8 for _ in texts]
        return self._embedder.encode(texts, normalize_embeddings=True).tolist()

    def upsert_records(self, document_id: int, records: List[Dict[str, Any]]):
        self._ensure()
        if not self._collection:
            return
        ids, docs, metas = [], [], []
        for r in records:
            rid = f"{document_id}:{r.get('row_index')}"
            text = " | ".join(f"{k}={r.get(k)}" for k in
                              ["date", "shift", "employee_no", "machine_no",
                               "work_order_no", "operation_code",
                               "quantity_produced", "time_taken_hours"] if r.get(k) is not None)
            ids.append(rid)
            docs.append(text or " ")
            metas.append({k: str(r.get(k)) for k in
                          ["date", "shift", "employee_no", "machine_no", "work_order_no"]
                          if r.get(k) is not None} | {"document_id": str(document_id),
                                                      "row_index": str(r.get("row_index"))})
        embs = self._embed(docs)
        try:
            self._collection.upsert(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
        except Exception as e:
            log.warning("vector upsert failed: %s", e)

    def search(self, query: str, top_k: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._ensure()
        if not self._collection:
            return []
        try:
            emb = self._embed([query])[0]
            res = self._collection.query(query_embeddings=[emb], n_results=top_k, where=filters)
            out = []
            for i, doc_id in enumerate(res.get("ids", [[]])[0]):
                out.append({
                    "id": doc_id,
                    "document": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "distance": res["distances"][0][i] if res.get("distances") else None,
                })
            return out
        except Exception as e:
            log.warning("vector search failed: %s", e)
            return []


vector_store = VectorStore()
