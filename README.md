# Genomics AI Platform (reference implementation)

An end-to-end, Git-deployable project that touches every item in the *AI Integration Specialist
(Healthcare & Genomics / AWS / RAG / .NET)* job description: pharmacogenomics (PGx) calling, ML model
serving, RAG chatbot with guardrails, vector search, ASP.NET Core gateway, Nextflow pipeline, Docker, CI/CD, AWS.

> **Not a medical device.** All patient data is synthetic, effect sizes are invented, and the allele tables are a small
> educational subset. See `docs/SAFETY.md`.

## Architecture
```
Client --JWT--> ASP.NET Core gateway (authZ, rate limit, audit, resilience)
                    |  X-Internal-Key
                    v
              FastAPI AI service
   ┌──────────────┼────────────────┬──────────────┐
   PGx engine   ML predictor    RAG + chat      VCF parser
 (rule-based)  (calibrated LR)  (hybrid search,  (streaming)
                                 guardrails)
                                    |
                          vector store: memory | pgvector
                          LLM: extractive | Bedrock (Converse)
Nextflow pipeline: VCF -> QC -> normalise -> /v1/pgx/from-vcf
```

## Quick start (no Docker, no cloud)
```bash
make setup && make test          # 79+ tests
make run                         # trains model, builds RAG index, serves :8000  (docs at /docs)
make demo                        # curl smoke test (in another shell)
```
Docker: `cp .env.example .env && docker compose up --build` (gateway :8080, AI service :8000).

## Layout
| Path | What |
|---|---|
| `services/ai-service` | Python: PGx engine, ML, RAG, chat, API, tests |
| `services/gateway` | ASP.NET Core 8: JWT, roles, rate limit, EF Core audit, Polly resilience, xunit tests |
| `pipelines/nextflow` | DSL2 pipeline with bcftools + AI call; docker and AWS Batch profiles |
| `infra/aws`, `scripts/` | AWS topology notes, SageMaker deploy script |
| `.github/workflows` | CI (lint, tests, docker, pipeline) and OIDC deploy |
| `docs/` | ARCHITECTURE, SAFETY, INTERVIEW_GUIDE, GLOSSARY |

## Configuration
Env vars prefixed `GAI_` (see `.env.example`). Switch to AWS with `GAI_EMBEDDER=bedrock GAI_LLM=bedrock`
(`pip install -e ".[aws]"`, AWS credentials, model access granted in Bedrock). The app refuses to start outside
`dev` with the default internal key.

## Verification status (honest)
| Part | Status |
|---|---|
| Python service, tests, ruff, live uvicorn smoke test | Run and passing |
| PyTorch MLP | Written; skipped locally (torch not installable in sandbox); CI runs it |
| ASP.NET Core gateway + tests | Written, never compiled (no .NET SDK in sandbox); CI builds it. Expect minor fixes on first build |
| Nextflow, Dockerfiles, compose | Written, YAML validated only; first CI run is the real test |
| AWS/Bedrock/SageMaker/pgvector paths | Written against documented APIs, not run against AWS |
