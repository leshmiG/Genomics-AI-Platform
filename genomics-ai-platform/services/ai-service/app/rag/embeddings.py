"""Embedding backends.

HashingEmbedder: deterministic, offline, no model download. Combines hashed word 1-2 grams
and hashed character 3-5 grams. It is a lexical-semantic baseline: good enough to run the
whole project without cloud credentials and to test retrieval logic, but a learned embedding
(Titan, Cohere, BioBERT-style, etc.) will retrieve better for paraphrases.

BedrockEmbedder: Amazon Titan Text Embeddings v2 through the Bedrock runtime.
"""

from __future__ import annotations

import json
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.clip(n, 1e-12, None)


class HashingEmbedder:
    name = "hashing-v1"

    def __init__(self, word_dim: int = 1024, char_dim: int = 2048):
        self._word = HashingVectorizer(
            n_features=word_dim, analyzer="word", ngram_range=(1, 2), alternate_sign=False,
            norm="l2", lowercase=True, stop_words="english",
        )
        self._char = HashingVectorizer(
            n_features=char_dim, analyzer="char_wb", ngram_range=(3, 5), alternate_sign=False,
            norm="l2", lowercase=True,
        )
        self.dim = word_dim + char_dim

    def embed(self, texts: list[str]) -> np.ndarray:
        w = self._word.transform(texts).toarray()
        c = self._char.transform(texts).toarray()
        return _l2(np.hstack([0.65 * w, 0.35 * c])).astype(np.float32)


class BedrockEmbedder:
    """Titan Text Embeddings v2. Pass `client` to inject a stub in tests."""

    def __init__(self, model_id: str, region: str, dim: int = 1024, client=None):
        self.name = f"bedrock:{model_id}:{dim}"
        self.dim = dim
        self.model_id = model_id
        if client is None:
            import boto3  # lazy: only needed when this backend is selected

            client = boto3.client("bedrock-runtime", region_name=region)
        self.client = client

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = []
        for t in texts:
            body = json.dumps({"inputText": t[:8000], "dimensions": self.dim, "normalize": True})
            resp = self.client.invoke_model(
                modelId=self.model_id, body=body, contentType="application/json", accept="application/json"
            )
            payload = json.loads(resp["body"].read())
            vecs.append(payload["embedding"])
        return _l2(np.asarray(vecs, dtype=np.float32))


def build_embedder(settings) -> Embedder:
    if settings.embedder == "bedrock":
        return BedrockEmbedder(settings.bedrock_embed_model, settings.aws_region)
    return HashingEmbedder()
