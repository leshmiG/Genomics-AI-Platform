"""Hybrid retrieval: dense vector search + BM25, fused with Reciprocal Rank Fusion (RRF)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .bm25 import BM25
from .chunking import Chunk
from .embeddings import Embedder
from .vector_store import VectorStore

RRF_K = 60  # standard constant from the original RRF paper


@dataclass
class Hit:
    chunk: Chunk
    dense_score: float  # cosine similarity in [-1, 1]
    bm25_score: float
    fused_score: float
    coverage: float = 0.0  # IDF-weighted share of query words present in the chunk, in [0, 1]


class HybridRetriever:
    def __init__(self, store: VectorStore, embedder: Embedder, candidate_pool: int = 12):
        self.store, self.embedder, self.pool = store, embedder, candidate_pool
        self._chunks = store.all_chunks()
        self._bm25 = BM25([c.text for c in self._chunks])
        self._by_id = {c.id: i for i, c in enumerate(self._chunks)}

    def search(self, query: str, k: int = 4) -> list[Hit]:
        if not self._chunks:
            return []
        qv = self.embedder.embed([query])[0]
        dense = self.store.search(qv, self.pool)
        dense_rank = {c.id: r for r, (c, _) in enumerate(dense)}
        dense_score = {c.id: s for c, s in dense}

        bm = np.asarray(self._bm25.scores(query))
        cov = self._bm25.coverage(query)
        bm_order = [i for i in np.argsort(-bm)[: self.pool] if bm[i] > 0]
        bm_rank = {self._chunks[i].id: r for r, i in enumerate(bm_order)}

        fused: dict[str, float] = {}
        for cid, r in dense_rank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r + 1)
        for cid, r in bm_rank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r + 1)

        hits = []
        for cid, f in sorted(fused.items(), key=lambda kv: -kv[1])[:k]:
            i = self._by_id[cid]
            hits.append(Hit(self._chunks[i], dense_score.get(cid, 0.0), float(bm[i]), f, cov[i]))
        return hits
