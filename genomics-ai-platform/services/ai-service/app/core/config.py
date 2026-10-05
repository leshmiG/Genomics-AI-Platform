"""Runtime configuration. Everything is overridable with GAI_* environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GAI_", env_file=".env", extra="ignore")

    env: str = "dev"
    # Shared secret between the .NET gateway and this service. Replace via Secrets Manager.
    internal_api_key: str = "dev-internal-key"

    model_dir: str = "artifacts/models"
    index_dir: str = "artifacts/index"
    knowledge_dir: str = "data/knowledge"

    # Pluggable backends. Defaults run fully offline (no cloud account needed).
    embedder: str = "hashing"  # hashing | bedrock
    llm: str = "extractive"  # extractive | bedrock
    vector_store: str = "memory"  # memory | pgvector
    pg_dsn: str | None = None

    # AWS. Pick a region where Bedrock and your chosen models are enabled and where your
    # data-residency rules allow processing. Do not assume a region supports a given model.
    aws_region: str = "eu-central-1"
    bedrock_embed_model: str = "amazon.titan-embed-text-v2:0"
    bedrock_llm_model: str = ""  # set to a model/inference-profile id enabled in your account
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str = "DRAFT"

    # RAG behaviour
    rag_top_k: int = 4
    # Grounding gate: answer only if the best passage covers >= this share of the query's
    # (IDF-weighted) content words, OR its dense cosine >= rag_min_dense. Tuned on a small
    # labelled set (tests/test_rag.py); re-tune with your own eval set when you change the
    # embedder. With a learned embedder, rely mainly on rag_min_dense.
    rag_min_coverage: float = 0.40
    rag_min_dense: float = 0.60
    chunk_chars: int = 900
    chunk_overlap: int = 150


@lru_cache
def get_settings() -> Settings:
    return Settings()
