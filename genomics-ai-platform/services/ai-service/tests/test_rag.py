import io
import json

import numpy as np
import pytest

from app.core.config import Settings
from app.rag.bm25 import BM25, stem, tokenize
from app.rag.chunking import chunk_markdown
from app.rag.embeddings import BedrockEmbedder, HashingEmbedder
from app.rag.ingest import ingest, load_retriever
from app.rag.vector_store import InMemoryVectorStore


@pytest.fixture(scope="module")
def settings(tmp_path_factory):
    d = tmp_path_factory.mktemp("idx")
    return Settings(index_dir=str(d), knowledge_dir="data/knowledge")


@pytest.fixture(scope="module")
def retriever(settings):
    assert ingest(settings) > 20
    return load_retriever(settings)


def test_chunker_respects_headings_and_size():
    md = "# Title\n\n## Alpha\n" + ("Sentence about alpha. " * 80) + "\n\n## Beta\nShort but meaningful beta section text here."
    chunks = chunk_markdown(md, "doc.md", max_chars=300, overlap=60)
    assert {c.heading for c in chunks} == {"Alpha", "Beta"}
    assert all(len(c.text) <= 300 + 80 for c in chunks)
    assert len({c.id for c in chunks}) == len(chunks)


def test_chunker_overlap_repeats_context():
    body = " ".join(f"Fact number {i} is stated here." for i in range(60))
    chunks = chunk_markdown(f"## H\n{body}", "d.md", max_chars=250, overlap=80)
    assert len(chunks) > 3
    # the end of one chunk should appear at the start of the next
    tail = chunks[0].text.split()[-3:]
    assert " ".join(tail) in chunks[1].text


def test_stem_and_tokenize_keep_identifiers_intact():
    assert stem("dosing") == stem("dosed") == stem("doses")
    assert "cyp2c19" in tokenize("CYP2C19 and rs4244285 with *17")
    assert "rs4244285" in tokenize("rs4244285")
    assert "*17" in tokenize("allele *17")


def test_bm25_prefers_exact_identifier():
    docs = ["alpha beta gamma", "rs4244285 defines CYP2C19 star two", "delta epsilon"]
    scores = BM25(docs).scores("rs4244285")
    assert int(np.argmax(scores)) == 1 and scores[0] == scores[2] == 0


def test_hashing_embedder_is_deterministic_normalised_and_semantic():
    e = HashingEmbedder()
    v = e.embed(["clopidogrel CYP2C19", "clopidogrel CYP2C19", "football world cup"])
    assert v.shape == (3, e.dim)
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5)
    assert np.allclose(v[0], v[1])
    assert float(v[0] @ v[1]) > float(v[0] @ v[2])


def test_store_roundtrip(tmp_path):
    e = HashingEmbedder()
    chunks = chunk_markdown("## A\nThis is the first passage about genomes and variants.\n\n## B\nThe second passage covers drug dosing and how dose adjustments are decided.", "x.md")
    assert len(chunks) == 2
    s = InMemoryVectorStore()
    s.add(chunks, e.embed([c.text for c in chunks]))
    s.save(tmp_path, e.name)
    s2 = InMemoryVectorStore.load(tmp_path)
    assert len(s2) == len(s) and s2.embedder_name == e.name
    top = s2.search(e.embed(["drug dosing"])[0], 1)[0][0]
    assert "dosing" in top.text


def test_embedder_mismatch_is_rejected(settings, tmp_path):
    ingest(settings.model_copy(update={"index_dir": str(tmp_path)}))
    meta = json.loads((tmp_path / "meta.json").read_text())
    meta["embedder"] = "something-else"
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    with pytest.raises(RuntimeError, match="Re-run ingestion"):
        load_retriever(settings.model_copy(update={"index_dir": str(tmp_path)}))


@pytest.mark.parametrize(
    "query, expected_source",
    [
        ("What does CYP2C19 poor metabolizer mean for clopidogrel?", "02_gene_drug_pairs.md"),
        ("what is a gVCF", "03_genomics_data_formats.md"),
        ("does removing names make genomic data anonymous", "05_data_governance_genomics.md"),
        ("how do I monitor model drift with PSI", "06_clinical_ml_safety.md"),
        ("why does phase matter for TPMT", "01_pharmacogenomics_basics.md"),
    ],
)
def test_retrieval_finds_the_right_document(retriever, query, expected_source):
    hits = retriever.search(query, 4)
    assert expected_source in {h.chunk.source for h in hits[:2]}


def test_exact_identifier_is_found_via_keyword_leg(retriever):
    hits = retriever.search("rs3918290", 3)
    assert hits and "rs3918290" in hits[0].chunk.text


RELEVANT = [
    "What does CYP2C19 poor metabolizer mean for clopidogrel?", "why does phase matter for TPMT",
    "what is a gVCF", "how do I monitor model drift with PSI", "does removing names make genomic data anonymous",
    "what is SLCO1B1 and simvastatin myopathy", "which cloud regions for data residency",
    "what is a star allele", "explain calibration of risk models", "what is a diplotype",
    "can I trust a VUS", "what tools normalise vcf files", "what is the difference between BAM and CRAM",
    "how is warfarin dosed with genetics", "how big is a whole genome",
]
OFF_TOPIC = [
    "best pizza recipe in Rome", "who won the football world cup", "how do I change a car tyre",
    "write me a poem about the sea", "what is the capital of Australia", "bitcoin price prediction tomorrow",
    "recommend a good laptop for gaming", "weather in Manama tomorrow", "how do I bake sourdough bread",
    "best restaurants in Bahrain",
]


def test_grounding_gate_separates_relevant_from_off_topic(retriever, settings):
    def passes(q):
        hits = retriever.search(q, settings.rag_top_k)
        return max(h.coverage for h in hits) >= settings.rag_min_coverage or \
            max(h.dense_score for h in hits) >= settings.rag_min_dense

    assert all(passes(q) for q in RELEVANT), [q for q in RELEVANT if not passes(q)]
    assert not any(passes(q) for q in OFF_TOPIC), [q for q in OFF_TOPIC if passes(q)]


class _FakeBedrockEmbedClient:
    def __init__(self):
        self.calls = 0

    def invoke_model(self, modelId, body, contentType, accept):  # noqa: N803 (boto3 signature)
        self.calls += 1
        req = json.loads(body)
        assert req["dimensions"] == 8 and req["normalize"] is True
        rng = np.random.default_rng(abs(hash(req["inputText"])) % (2**32))
        return {"body": io.BytesIO(json.dumps({"embedding": rng.normal(size=8).tolist()}).encode())}


def test_bedrock_embedder_with_stub_client():
    client = _FakeBedrockEmbedClient()
    e = BedrockEmbedder("amazon.titan-embed-text-v2:0", "eu-central-1", dim=8, client=client)
    v = e.embed(["a", "b"])
    assert v.shape == (2, 8) and client.calls == 2
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5)
    assert e.name.startswith("bedrock:")
