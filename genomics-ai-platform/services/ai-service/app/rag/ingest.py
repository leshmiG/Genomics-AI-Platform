"""Build the knowledge index.   python -m app.rag.ingest"""

from __future__ import annotations

from app.core.config import Settings, get_settings

from .chunking import load_directory
from .embeddings import Embedder, build_embedder
from .retriever import HybridRetriever
from .vector_store import InMemoryVectorStore, PgVectorStore, VectorStore


def build_store(settings: Settings, embedder: Embedder) -> VectorStore:
    if settings.vector_store == "pgvector":
        if not settings.pg_dsn:
            raise RuntimeError("GAI_PG_DSN must be set when GAI_VECTOR_STORE=pgvector")
        return PgVectorStore(settings.pg_dsn, embedder.dim)
    return InMemoryVectorStore()


def ingest(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    embedder = build_embedder(s)
    chunks = load_directory(s.knowledge_dir, s.chunk_chars, s.chunk_overlap)
    if not chunks:
        raise RuntimeError(f"No .md files found in {s.knowledge_dir}")
    store = build_store(s, embedder)
    store.add(chunks, embedder.embed([c.text for c in chunks]))
    if isinstance(store, InMemoryVectorStore):
        store.save(s.index_dir, embedder.name)
    return len(chunks)


def load_retriever(settings: Settings | None = None) -> HybridRetriever:
    s = settings or get_settings()
    embedder = build_embedder(s)
    if s.vector_store == "pgvector":
        store = build_store(s, embedder)
    else:
        store = InMemoryVectorStore.load(s.index_dir)
        if store.embedder_name != embedder.name:
            raise RuntimeError(
                f"Index built with '{store.embedder_name}' but runtime embedder is '{embedder.name}'. "
                "Re-run ingestion; mixing embedding models makes similarity meaningless."
            )
    return HybridRetriever(store, embedder)


if __name__ == "__main__":
    print(f"Indexed {ingest()} chunks")
