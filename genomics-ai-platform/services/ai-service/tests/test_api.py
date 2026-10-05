import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.genomics.vcf import render_demo_vcf
from app.main import app
from app.ml.cohort import FEATURES, make_cohort
from app.rag.ingest import ingest

KEY = {"X-Internal-Key": "test-key"}
BASE = {"age": 64, "bmi": 28, "egfr": 80, "ppi_use": 0, "diabetes": 0, "smoker": 0,
        "cyp2c19_phenotype": "Normal Metabolizer"}


@pytest.fixture(scope="module")
def client(model_dir, tmp_path_factory):
    idx = tmp_path_factory.mktemp("api_idx")
    mp = pytest.MonkeyPatch()
    mp.setenv("GAI_MODEL_DIR", str(model_dir))
    mp.setenv("GAI_INDEX_DIR", str(idx))
    mp.setenv("GAI_INTERNAL_API_KEY", "test-key")
    get_settings.cache_clear()
    ingest(get_settings())
    with TestClient(app) as c:
        yield c
    mp.undo()
    get_settings.cache_clear()


def test_health_and_ready_need_no_key(client):
    assert client.get("/health").json()["status"] == "ok"
    r = client.get("/ready")
    assert r.status_code == 200 and r.json()["model"] and r.json()["rag"]


def test_endpoints_require_key(client):
    assert client.post("/v1/chat", json={"message": "hi"}).status_code == 401
    assert client.post("/v1/chat", json={"message": "hi"}, headers={"X-Internal-Key": "wrong"}).status_code == 401


def test_request_id_roundtrip(client):
    assert client.get("/health", headers={"x-request-id": "abc123"}).headers["x-request-id"] == "abc123"
    assert len(client.get("/health").headers["x-request-id"]) == 16


def test_call_diplotype_with_guidance(client):
    r = client.post("/v1/pgx/call-diplotype", json={"gene": "CYP2C19", "diplotype": "*2/*2"}, headers=KEY)
    body = r.json()
    assert r.status_code == 200
    assert body["call"]["phenotype"] == "Poor Metabolizer"
    assert body["guidance"][0]["drug"] == "clopidogrel" and "Avoid" in body["guidance"][0]["recommendation"]
    assert "disclaimer" in body


def test_call_diplotype_validation(client):
    bad = client.post("/v1/pgx/call-diplotype", json={"gene": "CYP2C19", "diplotype": "2/2"}, headers=KEY)
    assert bad.status_code == 422
    unknown_gene = client.post("/v1/pgx/call-diplotype", json={"gene": "FOO", "diplotype": "*1/*2"}, headers=KEY)
    assert unknown_gene.status_code == 422
    unknown_allele = client.post("/v1/pgx/call-diplotype", json={"gene": "CYP2C19", "diplotype": "*1/*99"}, headers=KEY)
    assert unknown_allele.status_code == 422
    extra = client.post("/v1/pgx/call-diplotype", json={"gene": "CYP2C19", "diplotype": "*1/*2", "x": 1}, headers=KEY)
    assert extra.status_code == 422


def test_vcf_upload_end_to_end(client):
    vcf = render_demo_vcf({
        "PATIENT_A": {"rs4244285": "0/1"},
        "PATIENT_B": {"rs3918290": "1/1", "rs1800460": "1|0", "rs1142345": "0|1"},
    })
    r = client.post("/v1/pgx/from-vcf", files={"file": ("demo.vcf", vcf.encode(), "text/plain")}, headers=KEY)
    assert r.status_code == 200, r.text
    s = r.json()["samples"]
    assert s["PATIENT_A"]["genes"]["CYP2C19"]["phenotype"] == "Intermediate Metabolizer"
    assert s["PATIENT_B"]["genes"]["DPYD"]["phenotype"] == "Poor Metabolizer"
    assert s["PATIENT_B"]["genes"]["TPMT"]["diplotype"] == "*3B/*3C"
    drugs = {g["drug"] for g in s["PATIENT_B"]["guidance"]}
    assert {"fluorouracil", "azathioprine"} <= drugs


def test_vcf_rejects_garbage_and_oversize(client, monkeypatch):
    r = client.post("/v1/pgx/from-vcf", files={"file": ("x.vcf", b"not a vcf", "text/plain")}, headers=KEY)
    assert r.status_code == 422
    monkeypatch.setattr("app.main.MAX_VCF_BYTES", 10)
    r = client.post("/v1/pgx/from-vcf", files={"file": ("x.vcf", b"x" * 50, "text/plain")}, headers=KEY)
    assert r.status_code == 413


def test_prediction_and_validation(client):
    r = client.post("/v1/predict/clopidogrel-response", json=BASE, headers=KEY)
    assert r.status_code == 200 and 0 < r.json()["probability"] < 1
    assert r.json()["model_version"]
    for bad in ({**BASE, "age": 5}, {**BASE, "ppi_use": 2}, {**BASE, "cyp2c19_phenotype": "Super"}, {k: v for k, v in BASE.items() if k != "bmi"}):
        assert client.post("/v1/predict/clopidogrel-response", json=bad, headers=KEY).status_code == 422


def test_model_info_hides_reference_distribution(client):
    body = client.get("/v1/model", headers=KEY).json()
    assert "metrics" in body and "reference_distribution" not in body


def test_drift_endpoint(client):
    rows = make_cohort(300, 11)[FEATURES].to_dict("records")
    for r in rows:
        for col in ("age", "bmi", "egfr"):
            r[col] = float(r[col])
    ok = client.post("/v1/drift", json={"rows": rows}, headers=KEY).json()
    assert ok["overall"] in {"ok", "warn"}
    for r in rows:
        r["cyp2c19_phenotype"] = "Poor Metabolizer"
    assert client.post("/v1/drift", json={"rows": rows}, headers=KEY).json()["overall"] == "alert"


def test_rag_search_and_chat(client):
    s = client.post("/v1/rag/search", json={"query": "what is a gVCF", "k": 2}, headers=KEY).json()
    assert len(s["hits"]) == 2 and "03_genomics_data_formats.md" in {h["source"] for h in s["hits"]}
    c = client.post("/v1/chat", json={"message": "What is a diplotype?", "session_id": "t1"}, headers=KEY).json()
    assert c["grounded"] and c["citations"]
    off = client.post("/v1/chat", json={"message": "best pizza in Rome", "session_id": "t1"}, headers=KEY).json()
    assert not off["grounded"]
    assert client.post("/v1/chat", json={"message": "x" * 3000}, headers=KEY).status_code == 422
    assert client.post("/v1/chat", json={"message": "hi", "session_id": "bad id!"}, headers=KEY).status_code == 422


def test_metrics_exposed(client):
    client.get("/health")
    text = client.get("/metrics").text
    assert "gai_requests_total" in text and "gai_predictions_total" in text


def test_not_ready_when_artifacts_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("GAI_MODEL_DIR", str(tmp_path / "none"))
    monkeypatch.setenv("GAI_INDEX_DIR", str(tmp_path / "none"))
    monkeypatch.setenv("GAI_INTERNAL_API_KEY", "test-key")
    get_settings.cache_clear()
    with TestClient(app) as c:
        assert c.get("/ready").status_code == 503
        assert c.post("/v1/predict/clopidogrel-response", json=BASE, headers=KEY).status_code == 503
        assert c.get("/health").status_code == 200
    get_settings.cache_clear()
