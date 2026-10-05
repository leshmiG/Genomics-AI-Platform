"""Vector stores: in-memory (default, file-persisted) and PostgreSQL + pgvector.

Both implement the same tiny interface so retrieval code does not care where vectors live.
Interview note: exact (flat) search is fine below ~100k chunks. Beyond that use an ANN index
(HNSW or IVFFlat in pgvector) and accept an approximate-recall / latency trade-off.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import numpy as np

from .chunking import Chunk


class VectorStore(Protocol):
    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None: ...
    def search(self, vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]: ...
    def all_chunks(self) -> list[Chunk]: ...
    def __len__(self) -> int: ...


class InMemoryVectorStore:
    """Cosine similarity over L2-normalised vectors held in a numpy matrix."""

    def __init__(self):
        self._chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None
        self.embedder_name: str | None = None

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        self._chunks.extend(chunks)
        self._matrix = vectors if self._matrix is None else np.vstack([self._matrix, vectors])

    def search(self, vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        if self._matrix is None or not len(self._chunks):
            return []
        scores = self._matrix @ vector.astype(np.float32)
        order = np.argsort(-scores)[:k]
        return [(self._chunks[i], float(scores[i])) for i in order]

    def all_chunks(self) -> list[Chunk]:
        return list(self._chunks)

    def __len__(self) -> int:
        return len(self._chunks)

    # persistence -------------------------------------------------------------------
    def save(self, directory: str | Path, embedder_name: str) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "vectors.npy", self._matrix if self._matrix is not None else np.zeros((0, 0)))
        (d / "chunks.jsonl").write_text("\n".join(json.dumps(c.as_dict()) for c in self._chunks))
        (d / "meta.json").write_text(json.dumps({"embedder": embedder_name, "count": len(self._chunks)}))

    @classmethod
    def load(cls, directory: str | Path) -> InMemoryVectorStore:
        d = Path(directory)
        if not (d / "meta.json").exists():
            raise FileNotFoundError(f"No index in {d}. Run: python -m app.rag.ingest")
        store = cls()
        meta = json.loads((d / "meta.json").read_text())
        lines = (d / "chunks.jsonl").read_text().splitlines()
        store._chunks = [Chunk(**json.loads(line)) for line in lines if line.strip()]
        store._matrix = np.load(d / "vectors.npy")
        store.embedder_name = meta["embedder"]
        return store


class PgVectorStore:
    """PostgreSQL + pgvector. `<=>` is cosine distance, so score = 1 - distance.

    Requires: pip install 'psycopg[binary]' pgvector ; and `CREATE EXTENSION vector` rights.
    Integration-tested only when GAI_TEST_PG_DSN is set (see tests/test_pgvector.py).
    """

    def __init__(self, dsn: str, dim: int, table: str = "kb_chunks"):
        import psycopg  # lazy import
        from pgvector.psycopg import register_vector

        if not table.isidentifier():
            raise ValueError("invalid table name")
        self.table, self.dim = table, dim
        self.conn = psycopg.connect(dsn, autocommit=True)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.conn)
        self.conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY, source TEXT, heading TEXT, body TEXT,
                embedding vector({dim}))"""
        )
        self.conn.execute(
            f"CREATE INDEX IF NOT EXISTS {table}_hnsw ON {table} USING hnsw (embedding vector_cosine_ops)"
        )

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        with self.conn.cursor() as cur:
            for c, v in zip(chunks, vectors, strict=True):
                cur.execute(
                    f"""INSERT INTO {self.table} (id, source, heading, body, embedding)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT (id) DO UPDATE SET body = EXCLUDED.body,
                        heading = EXCLUDED.heading, embedding = EXCLUDED.embedding""",
                    (c.id, c.source, c.heading, c.text, v),
                )

    def search(self, vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, source, heading, body, 1 - (embedding <=> %s) AS score
                    FROM {self.table} ORDER BY embedding <=> %s LIMIT %s""",
                (vector, vector, k),
            )
            return [(Chunk(r[0], r[1], r[2], r[3]), float(r[4])) for r in cur.fetchall()]

    def all_chunks(self) -> list[Chunk]:
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT id, source, heading, body FROM {self.table} ORDER BY id")
            return [Chunk(*r) for r in cur.fetchall()]

    def __len__(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self.table}")
            return int(cur.fetchone()[0])
