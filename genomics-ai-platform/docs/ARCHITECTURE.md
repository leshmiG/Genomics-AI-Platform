# Architecture and design decisions

## Why two services
The JD asks for both ML/AI (Python ecosystem) and ASP.NET Core integration. The gateway owns cross-cutting concerns
(identity, authorisation, rate limiting, audit, resilience) so the AI service can stay a simple, internal compute
service. The gateway never stores request bodies, as genomic data is identifying.

## Key decisions
1. **Rules, not LLMs, make clinical calls.** Diplotype -> phenotype -> guidance is deterministic, versioned and testable.
   The LLM only explains retrieved text, and the chat tool calls the deterministic engine for any gene+diplotype.
2. **Model choice by evidence.** Logistic regression vs gradient boosting, with a parsimony margin, then sigmoid calibration.
   Calibration (Brier, ECE) matters more than AUC for risk communication. Subgroup metrics are reported.
3. **Hybrid retrieval.** Dense + BM25 fused with RRF (k=60), then a *grounding gate* (IDF-weighted query coverage + dense
   score). Below the gate, the bot refuses instead of guessing. The gate uses the current message only, so history
   cannot launder an off-topic question.
4. **Embedder mismatch guard.** The index stores embedder name/dimension; loading with a different embedder fails loudly.
5. **Fail-closed defaults.** No default secrets outside dev, strict pydantic schemas (`extra=forbid`), size caps.
6. **Observability without PHI.** Request IDs end to end, Prometheus metrics, logs carry no payloads.

## Resilience (gateway -> AI service)
Timeout per attempt and total, 2 retries with jitter, circuit breaker. Safe because calls are pure computations. Upstream 4xx
is relayed unchanged; connectivity failures become 503 with no payload logged.

## MLOps path
Train in CI -> model card (data hash, metrics, reference distribution) -> registry -> promote only if gates pass ->
serve with version in every response -> monitor PSI drift (0.1 warn / 0.25 alert, min 200 samples) -> retrain trigger.

## Scaling notes
In-memory vector store is for demos; use pgvector (HNSW) or OpenSearch for a national dataset. Pipelines move to AWS Batch/HealthOmics.
Large VCFs should be streamed from S3 to a worker queue rather than uploaded through the API.
