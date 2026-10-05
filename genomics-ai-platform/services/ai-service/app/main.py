"""FastAPI application.

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000

Security model: this service is meant to sit BEHIND the .NET gateway on a private network.
The gateway authenticates users (JWT) and forwards requests with a shared internal key.
Logs never contain request bodies, genotypes or chat text.
"""

from __future__ import annotations

import hmac
import logging
import time
import uuid
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app import __version__
from app.chat.llm import build_llm
from app.chat.service import ChatService
from app.core.config import get_settings
from app.genomics import guidance
from app.genomics.pgx import call_all, call_from_diplotype
from app.genomics.vcf import VcfError, parse_vcf
from app.ml.cohort import FEATURES
from app.ml.drift import drift_report
from app.ml.predictor import ModelNotReady, Predictor
from app.rag.ingest import load_retriever
from app.schemas import ChatRequest, DiplotypeRequest, DriftRequest, PredictRequest, SearchRequest

log = logging.getLogger("gai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

REQUESTS = Counter("gai_requests_total", "HTTP requests", ["route", "method", "status"])
LATENCY = Histogram("gai_request_seconds", "Request latency", ["route"])
PREDICTIONS = Counter("gai_predictions_total", "Risk predictions by band", ["band", "model_version"])
CHAT = Counter("gai_chat_total", "Chat outcomes", ["outcome"])
DRIFT = Counter("gai_drift_checks_total", "Drift checks by overall status", ["status"])

MAX_VCF_BYTES = 20 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.settings = s
    app.state.predictor = app.state.retriever = app.state.chat = None
    app.state.startup_errors = {}
    try:
        app.state.predictor = Predictor(s.model_dir)
    except ModelNotReady as exc:
        app.state.startup_errors["model"] = str(exc)
    try:
        app.state.retriever = load_retriever(s)
        app.state.chat = ChatService(app.state.retriever, build_llm(s), s)
    except Exception as exc:  # index missing, backend misconfigured, ...
        app.state.startup_errors["rag"] = f"{type(exc).__name__}: {exc}"
    if s.env != "dev" and s.internal_api_key == "dev-internal-key":
        raise RuntimeError("GAI_INTERNAL_API_KEY must be changed outside dev")
    for k, v in app.state.startup_errors.items():
        log.warning("startup: %s not ready: %s", k, v)
    yield


app = FastAPI(title="Genomics AI Service", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def observability(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = rid
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        dur = time.perf_counter() - start
        REQUESTS.labels(path, request.method, str(status)).inc()
        LATENCY.labels(path).observe(dur)
        log.info("rid=%s %s %s -> %s %.0fms", rid, request.method, path, status, dur * 1000)


def require_key(request: Request, x_internal_key: str | None = Header(default=None)) -> None:
    expected = request.app.state.settings.internal_api_key
    if not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(status_code=401, detail="invalid or missing internal key")


def _state(request: Request, name: str, err_key: str):
    obj = getattr(request.app.state, name)
    if obj is None:
        raise HTTPException(503, detail=request.app.state.startup_errors.get(err_key, "not ready"))
    return obj


# ---------------------------------------------------------------------------- ops
@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/ready")
def ready(request: Request):
    errs = request.app.state.startup_errors
    body = {"model": "model" not in errs, "rag": "rag" not in errs, "errors": errs}
    return JSONResponse(body, status_code=200 if not errs else 503)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------- PGx
@app.post("/v1/pgx/call-diplotype", dependencies=[Depends(require_key)])
def call_diplotype(body: DiplotypeRequest):
    try:
        call = call_from_diplotype(body.gene, body.diplotype)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    drugs = body.drugs or [d for d in guidance.SUPPORTED_DRUGS if guidance.DRUG_TO_GENE[d] == body.gene]
    recs = []
    for d in drugs:
        g = guidance.lookup(d, call.phenotype)
        if g is None:
            raise HTTPException(422, detail=f"Unsupported drug '{d}'. Supported: {guidance.SUPPORTED_DRUGS}")
        if g.gene == body.gene:
            recs.append(g.__dict__)
    return {"call": call.as_dict(), "guidance": recs, "guidance_source": guidance.GUIDELINE_SOURCE,
            "disclaimer": guidance.DISCLAIMER}


@app.post("/v1/pgx/from-vcf", dependencies=[Depends(require_key)])
async def pgx_from_vcf(file: UploadFile = File(...)):
    data = await file.read(MAX_VCF_BYTES + 1)
    if len(data) > MAX_VCF_BYTES:
        raise HTTPException(413, detail=f"VCF larger than {MAX_VCF_BYTES // (1024 * 1024)} MB; use the pipeline")
    try:
        parsed = parse_vcf(data)
    except VcfError as exc:
        raise HTTPException(422, detail=str(exc)) from exc

    samples = {}
    for name, gts in parsed.samples.items():
        calls = call_all(gts)
        recs = []
        for drug in guidance.SUPPORTED_DRUGS:
            gene = guidance.DRUG_TO_GENE[drug]
            g = guidance.lookup(drug, calls[gene].phenotype)
            if g:
                recs.append(g.__dict__)
        samples[name] = {"genes": {g: c.as_dict() for g, c in calls.items()}, "guidance": recs}
    return {
        "records_seen": parsed.records_seen, "records_used": parsed.records_used,
        "warnings": parsed.warnings[:50], "samples": samples,
        "guidance_source": guidance.GUIDELINE_SOURCE, "disclaimer": guidance.DISCLAIMER,
    }


# ---------------------------------------------------------------------------- ML
@app.post("/v1/predict/clopidogrel-response", dependencies=[Depends(require_key)])
def predict(body: PredictRequest, request: Request):
    p: Predictor = _state(request, "predictor", "model")
    out = p.predict(body.model_dump())
    PREDICTIONS.labels(out["risk_band"], out["model_version"]).inc()
    return out


@app.get("/v1/model", dependencies=[Depends(require_key)])
def model_info(request: Request):
    p: Predictor = _state(request, "predictor", "model")
    c = p.card
    return {k: c[k] for k in ("model_name", "version", "algorithm", "features", "metrics",
                              "subgroup_metrics", "risk_bands", "intended_use", "limitations", "training")}


@app.post("/v1/drift", dependencies=[Depends(require_key)])
def drift(body: DriftRequest, request: Request):
    p: Predictor = _state(request, "predictor", "model")
    df = pd.DataFrame([r.model_dump() for r in body.rows])[FEATURES]
    rep = drift_report(df, p.card["reference_distribution"])
    DRIFT.labels(rep["overall"]).inc()
    return {**rep, "model_version": p.version}


# ---------------------------------------------------------------------------- RAG / chat
@app.post("/v1/rag/search", dependencies=[Depends(require_key)])
def rag_search(body: SearchRequest, request: Request):
    r = _state(request, "retriever", "rag")
    hits = r.search(body.query, body.k)
    return {"hits": [
        {"id": h.chunk.id, "source": h.chunk.source, "heading": h.chunk.heading, "text": h.chunk.text,
         "dense_score": round(h.dense_score, 4), "bm25_score": round(h.bm25_score, 3),
         "coverage": round(h.coverage, 3), "fused_score": round(h.fused_score, 5)} for h in hits]}


@app.post("/v1/chat", dependencies=[Depends(require_key)])
def chat(body: ChatRequest, request: Request):
    svc: ChatService = _state(request, "chat", "rag")
    resp = svc.answer(body.message, body.session_id)
    outcome = "grounded" if resp.grounded else (resp.flags[-1] if resp.flags else "ungrounded")
    CHAT.labels(outcome.split(":")[0]).inc()
    return resp.as_dict()
