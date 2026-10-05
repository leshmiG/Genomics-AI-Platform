# Technical interview guide: AI Integration Specialist (Healthcare & Genomics / AWS / RAG / .NET)

How to use: each section lists **what is tested**, then questions with **model answers**. Answers are written so you
can say them in 60-120 seconds. Where the repo implements the topic, the file is named so you can *show* it.

## 0. Honest gap assessment (read first)
Your CV shows data engineering (AWS, Power BI, SAP), not production ML, healthcare/genomics or .NET. Interviewers
will probe exactly there. Strategy: do not bluff. Say "I haven't run X in production; here is what I built and
what I know", then go deep on the project. Priority order for study: (1) RAG + Bedrock, (2) scikit-learn evaluation and calibration,
(3) PGx domain basics, (4) ASP.NET Core basics (read `services/gateway`), (5) Docker/Git/CI, (6) SageMaker/MLOps, (7) PyTorch/TensorFlow, (8) Nextflow.
Be ready for "have you used .NET professionally?": answer truthfully, then explain the gateway you built and what you'd learn first.

## 1. "Tell me about your project" (2-minute script)
"I built a reference platform for pharmacogenomics on synthetic data. A rule-based engine turns diplotypes into
metabolizer phenotypes and guideline-style guidance, so clinical calls are deterministic and testable. A calibrated
scikit-learn model estimates clopidogrel poor-response risk; I chose logistic regression over gradient boosting because
it was within a parsimony margin and better calibrated, and I report subgroup metrics and PSI drift. A RAG chatbot uses hybrid
retrieval (dense plus BM25 with reciprocal rank fusion) and a grounding gate that refuses instead of guessing; it
redacts PII, resists prompt injection and refuses personal dosing advice. An ASP.NET Core gateway handles JWT, roles, rate
limiting, audit and resilience; a Nextflow pipeline processes VCFs; everything is containerised with CI/CD to AWS.
It is not a medical device and the data is synthetic; the point is the engineering and the safety design."
Likely follow-ups: why rules not LLM for calls; how you'd validate on real data; what you'd do differently; what broke (grounding gate bug, history leaking into gate: say it).

## 2. Python and scikit-learn
**Tested:** pipelines, leakage, metrics, calibration, imbalance, cross-validation, reproducibility.
1. **What is data leakage and how did you avoid it?** Information from test/validation leaks into training: fitting scalers/encoders on all data, features derived from the label, random splits on repeated patients. Fit preprocessing inside a Pipeline on the training fold only; split by patient/family, not row; time-split for temporal data.
2. **AUC vs calibration, which matters?** AUC measures ranking; clinicians use the probability, so calibration (Brier, reliability curve, ECE) matters. A high-AUC model can say 90% when truth is 60%. I calibrate with sigmoid/Platt (few data) or isotonic (lots of data, can overfit) using CalibratedClassifierCV on held-out folds.
3. **Class imbalance?** Prefer proper scoring rules and threshold choice by cost over blind resampling; class_weight, stratified splits, PR-AUC; SMOTE only inside CV folds. Resampling distorts probabilities, so recalibrate.
4. **Why logistic regression over boosting?** Small tabular data, monotone interpretable effects, better calibration, easier audit. Boosting only if it beats LR by a margin that survives CV (I use a parsimony margin).
5. **Cross-validation choices?** Stratified K-fold; GroupKFold when samples are correlated; nested CV for tuning plus honest estimate; repeated CV for stability.
6. **Explain regularisation.** L2 shrinks coefficients (ridge), L1 sparsifies (lasso); controls variance; scale features first; C is inverse strength.
7. **Bias-variance?** Underfit = high bias, overfit = high variance; diagnose via learning curves.
8. **How do you explain a model?** Coefficients for LR; permutation importance; SHAP; I used occlusion (replace a feature with reference value) which is simple and model-agnostic. Caveat: correlated features, explanations are not causal.
9. **How do you evaluate subgroups/fairness?** Report AUC, calibration and error rates per group (the cohort has groups A/B/C with different allele frequencies); look for calibration gaps; population stratification matters in genetics.
10. **Reproducibility?** Seeds, pinned versions, data hash in the model card, versioned artefacts, deterministic pipelines.
11. **Handle missing data?** Missingness mechanism (MCAR/MAR/MNAR); impute inside the pipeline; add indicator features; for clinical data, "missing" can be informative.
12. **Coding task likely:** write a function to compute ECE; implement stratified split; parse a VCF line; reverse a list; group-by aggregate in pandas. Practise 5 of each.
```python
def ece(y, p, bins=10):
    import numpy as np
    y, p = np.asarray(y), np.asarray(p); e = 0.0
    edges = np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p > lo) & (p <= hi)
        if m.any(): e += m.mean() * abs(y[m].mean() - p[m].mean())
    return e
```

## 3. TensorFlow / PyTorch
**Tested:** training loop, tensors, overfitting controls, serving, when deep learning is justified.
1. **Write a PyTorch training loop.** zero_grad -> forward -> loss -> backward -> step; model.train()/eval(); torch.no_grad() for validation (see `app/ml/torch_model.py`).
2. **BCEWithLogitsLoss vs sigmoid+BCE?** The fused version is numerically stable (log-sum-exp).
3. **Dropout, weight decay, early stopping.** Regularisers; early stop on a proper scoring rule such as validation Brier/log loss.
4. **Eager vs graph (TF)?** TF2 eager by default; tf.function traces to graphs for speed/export; SavedModel for serving (TF Serving/SageMaker).
5. **When is deep learning justified in genomics?** Sequence models (variant effect prediction, DeepVariant-style image models), imaging, unstructured notes; for small tabular clinical data, linear/boosted models usually win.
6. **Transfer learning / embeddings?** Pretrained encoders produce embeddings reused for retrieval/classification; fine-tune only with adequate labelled data.
7. **Export for inference?** TorchScript/ONNX; batch size and dynamic axes; quantisation for CPU latency.
8. **Vanishing gradients, batch norm, LR schedules, gradient clipping**: know one sentence each.
9. **Honest answer:** "My hands-on depth is scikit-learn; I wrote and tested a PyTorch MLP on the same task and compared."

## 4. MLOps and AWS SageMaker
1. **Describe an ML lifecycle on AWS.** Data in S3 -> processing (Glue/SageMaker Processing) -> training jobs -> experiment tracking -> Model Registry with approval -> endpoint (real-time/serverless/async/batch transform) -> Model Monitor (data quality, drift, bias) -> retraining via Pipelines/Step Functions, CI/CD with CodePipeline/GitHub Actions.
2. **Real-time vs async vs batch?** Real-time: low latency, always on. Serverless: spiky, cold starts. Async: large payloads/long inference (queue + S3). Batch transform: offline scoring.
3. **Drift types?** Data drift (covariate), label/prior shift, concept drift. I use PSI per feature (0.1 warn, 0.25 alert, min 200 samples); labels in healthcare arrive late, so monitor inputs and outcome proxies.
4. **Model promotion gates?** Metrics threshold, calibration, subgroup gaps, data validation, security scan, human approval for clinical models.
5. **Model card contents?** Intended use, data description/hash, metrics, subgroup results, limitations, version, reference distribution.
6. **Blue/green, canary, shadow?** Shadow compares new vs old silently; canary shifts a small share; rollback by switching variant weights.
7. **Feature store?** Consistent features online/offline (SageMaker Feature Store); avoid train/serve skew.
8. **Cost control?** Right-size instances, serverless/async, spot for training, autoscaling, endpoints deleted in dev.
9. **IAM for SageMaker?** Separate execution roles, least privilege, VPC-only, KMS, no internet for training containers with PHI.

## 5. Amazon Bedrock, RAG and vector databases
**Core topic of the role.** Be able to draw the pipeline: ingest -> chunk -> embed -> index -> retrieve -> (rerank) -> prompt -> generate -> verify/cite.
1. **Why RAG over fine-tuning?** Fresh, citable, access-controlled knowledge without retraining; fine-tuning for style/format/behaviour.
2. **Chunking strategy?** Heading-aware, 600-1000 chars with ~15% overlap (mine: 900/150); keep metadata (source, heading); too small loses context, too big dilutes retrieval.
3. **Dense vs sparse vs hybrid?** Dense captures semantics; BM25 captures exact tokens (gene names, rsIDs). Hybrid with Reciprocal Rank Fusion (score = sum 1/(k+rank), k=60) is robust without score normalisation.
4. **Vector index types?** Flat (exact), HNSW (graph, high recall, memory heavy), IVF (clusters, needs training). Tune ef_search/M; metric cosine vs inner product (normalise vectors).
5. **Vector DB options?** pgvector (simple, SQL joins, my choice), OpenSearch (hybrid, scale), Aurora pgvector, Bedrock Knowledge Bases (managed), Pinecone/Weaviate/Qdrant. Choose by scale, filtering needs, ops burden and residency.
6. **How do you stop hallucination?** Grounding gate (IDF-weighted coverage + dense score thresholds); refuse when ungrounded; temperature 0; cite chunks; deterministic tools for facts; post-hoc claim checking; evals.
7. **How did you pick thresholds?** Measured separation on relevant vs off-topic queries, locked in a test. Say it is a heuristic; production uses labelled eval sets.
8. **Evaluate RAG?** Retrieval: recall@k, MRR, nDCG on labelled query-chunk pairs. Generation: faithfulness/groundedness, answer relevance, citation accuracy (RAGAS-style or LLM-as-judge with spot human review). Safety: red-team set (injection, PII, dosing).
9. **Prompt injection and RAG poisoning?** Treat retrieved text as data not instructions; delimit; heuristics; Bedrock Guardrails (denied topics, PII filters, contextual grounding check); least-privilege tools; ingest only vetted documents.
10. **Bedrock API basics.** `bedrock-runtime` Converse API (unified chat), InvokeModel for model-specific payloads, embeddings via Titan Text Embeddings v2; Guardrails attach with guardrailIdentifier/version; model access must be enabled per region/account.
11. **Multi-turn memory?** Bounded session store; condense follow-ups; gate on the current message only (I fixed a bug where history let an off-topic query pass).
12. **Reranking?** Cross-encoder/Cohere rerank on top-20 -> top-4; improves precision at latency cost.
13. **Embedding changes?** Re-embed everything; store embedder name/dimension in the index and refuse mismatches (implemented).
14. **Latency/cost levers?** Cache embeddings/answers, smaller models, streaming, limit context, prompt caching.
15. **Agents/tool use?** The LLM selects a tool; execution is validated and deterministic (pgx lookup). LangGraph/LangChain are orchestration; I can explain the loop even if I used plain Python.
16. **PHI to an LLM?** Redact first, no training on data, VPC endpoints, region control, DPA, logging without payloads.

## 6. Genomics and pharmacogenomics (domain)
1. **What is PGx?** How inherited variation affects drug response: metabolism (CYPs), transport (SLCO1B1), targets, adverse reactions (HLA). Used to choose drug/dose.
2. **Star allele, haplotype, diplotype, phenotype?** A star allele names a haplotype (set of variants on one chromosome copy). Diplotype = the two haplotypes (*1/*2). Phenotype = predicted function (Poor/Intermediate/Normal/Rapid/Ultrarapid Metabolizer), via function scores or activity scores.
3. **Activity score?** Alleles get 0/0.5/1 etc.; the sum maps to a phenotype (CYP2C9, DPYD). SLCO1B1 uses transporter function labels.
4. **Why does phase matter?** Unphased heterozygous calls can be cis or trans. TPMT *3A (two variants on one haplotype) heterozygous looks like *3B/*3C (one each on separate haplotypes) unphased, but phenotypes differ. My engine enumerates haplotype pairs and returns "Indeterminate" when phenotypes differ. Phase comes from long reads, trio data, statistical phasing.
5. **Example gene-drug pairs.** CYP2C19-clopidogrel (poor metabolizers get reduced activation), SLCO1B1-simvastatin (myopathy), TPMT/NUDT15-azathioprine (myelosuppression), DPYD-fluorouracil (severe toxicity), CYP2C9/VKORC1-warfarin, HLA-B*57:01-abacavir, HLA-B*15:02-carbamazepine, CYP2D6-codeine/tamoxifen.
6. **CPIC vs DPWG vs PharmGKB vs PharmVar?** CPIC and DPWG publish guidelines; PharmGKB curates evidence and annotations; PharmVar is the star-allele nomenclature authority.
7. **Why is CYP2D6 hard?** Gene deletions, duplications, hybrids with CYP2D7, high variant density; needs copy-number-aware tools (Stargazer, Cyrius, Aldy). I explicitly excluded it.
8. **File formats.** FASTQ (reads+quality), BAM/CRAM (alignments), VCF (variants), gVCF (adds reference blocks so homozygous-reference is distinguishable from no-call), BED (regions), FASTA (reference). GT field: `0/1` unphased, `0|1` phased; alleles index REF=0, ALT=1.
9. **Reference build issues.** GRCh37 vs GRCh38 coordinates differ; liftover; match by rsID plus REF/ALT check (the parser warns on mismatches). Chr naming (`chr1` vs `1`).
10. **Normalisation.** `bcftools norm` left-aligns indels and splits multi-allelic sites so identical variants compare equal.
11. **Pipeline stages.** QC (FastQC) -> trim -> align (BWA-MEM2) -> mark duplicates -> base recalibration -> variant calling (GATK HaplotypeCaller / DeepVariant) -> joint genotyping -> filtration -> annotation (VEP/ANNOVAR/SnpEff) -> interpretation.
12. **ACMG/AMP classification.** Pathogenic, Likely pathogenic, VUS, Likely benign, Benign, from evidence (population frequency, computational, functional, segregation). Not the same as PGx function.
13. **Population databases.** gnomAD, 1000 Genomes, ClinVar. Under-representation of Arab/Middle-Eastern cohorts matters: allele frequencies and reference panels may not transfer, which is why national datasets (e.g., Bahrain Genome) have value.
14. **Bias and stratification.** Ancestry confounds genotype-phenotype models; use PCA covariates, subgroup evaluation, local-ancestry-aware panels.
15. **Clinical data standards.** HL7 FHIR (Genomics Reporting IG), OMOP CDM, LOINC, SNOMED CT, ICD-10, HPO for phenotypes, HGVS for variant names, VRS/GA4GH standards (Beacon, htsget, Phenopackets).
16. **Privacy.** Genome data is identifying even if de-identified; relatives are affected; use controlled access, federated analysis, consent management, minimum necessary.
17. **Limits you should volunteer.** Preemptive testing is not equal to clinical validity; non-genetic factors (age, drugs, kidney function) matter; guideline content changes, so version it.

## 7. Nextflow and pipelines
1. **Why Nextflow?** Reproducible, portable (local, Slurm, AWS Batch, HealthOmics), containerised, resumable (`-resume`), dataflow model; nf-core provides vetted pipelines.
2. **Core concepts.** Process (task with script/container), channel (async queue), workflow, operators (map, collect, groupTuple, join), `publishDir`, config profiles, work directory cache.
3. **How does -resume work?** Hash of inputs, script and container; unchanged tasks reuse cached outputs.
4. **Scaling on AWS.** `awsbatch` executor, S3 work dir, Fusion/Wave optionally; AWS HealthOmics workflows is managed Nextflow/WDL/CWL, built for omics with sequence stores. Cost: spot, right-sized containers, retries on spot reclaim (`errorStrategy 'retry'`).
5. **Nextflow vs Snakemake vs WDL/Cromwell vs Airflow?** Nextflow/Snakemake/WDL are bioinformatics workflow engines with file-based dataflow; Airflow orchestrates generic scheduled jobs. Use Airflow/Step Functions around them.
6. **Testing pipelines.** Small test profile, nf-test, container version pinning, checksum outputs, CI run (see `ci.yml`).
7. **Provenance.** Record container digests, pipeline version, parameters, reference build, tool versions: required for clinical reproducibility.

## 8. ASP.NET Core, REST and microservices
1. **Request pipeline/middleware?** Ordered delegates; order matters (UseAuthentication -> UseRateLimiter -> UseAuthorization -> custom). Show `Program.cs`.
2. **Minimal APIs vs controllers?** Minimal APIs: less ceremony, good for small services; controllers: filters, model binding conventions, larger teams. Both fine.
3. **DI lifetimes?** Singleton, Scoped (per request, EF DbContext), Transient. Do not inject Scoped into Singleton (captive dependency).
4. **JWT auth?** Validate issuer, audience, signature, lifetime; roles from claims; in production use an IdP (Cognito/Entra) with Authority/JWKS, not a shared symmetric key. Policy-based authorisation (`RequireRole`).
5. **HttpClient pitfalls?** Do not `new HttpClient()` per call (socket exhaustion); use IHttpClientFactory/typed clients; resilience via Microsoft.Extensions.Http.Resilience (Polly v8): retry with jitter, circuit breaker, timeouts, hedging.
6. **Idempotency and retries?** Retry only idempotent calls; use idempotency keys for POSTs with side effects.
7. **Rate limiting?** Built-in `AddRateLimiter` (fixed/sliding window, token bucket, concurrency); partition per user/IP; 429 plus Retry-After.
8. **EF Core?** DbContext is a unit of work, tracks changes; migrations; `AsNoTracking` for reads; N+1 and Include; concurrency tokens; raw SQL when needed. Audit table design: no PHI.
9. **async/await?** Never `.Result`/`.Wait()` (deadlocks/thread starvation); pass CancellationToken; `ConfigureAwait` rarely matters in ASP.NET Core.
10. **REST design.** Resource nouns, correct status codes (201, 202 for async, 409, 422, 429, 503), versioning (`/v1`), pagination, problem+json (RFC 7807), idempotent PUT/DELETE, OpenAPI.
11. **Microservices trade-offs.** Independent deploy/scale vs distributed complexity; start modular, split on real boundaries; sync REST vs async messaging (SQS/SNS/EventBridge); outbox pattern; saga for multi-step; distributed tracing (OpenTelemetry, correlation IDs).
12. **Health checks.** Liveness (`/health`) vs readiness (`/ready`, checks model/index/db), used by ALB/ECS/Kubernetes.
13. **Testing.** xunit + WebApplicationFactory + stubbed HttpMessageHandler (see `GatewayTests.cs`).
14. **Calling Python from .NET.** Options: HTTP/gRPC to a Python service (my choice), ONNX Runtime in-process, ML.NET, SageMaker endpoint via AWSSDK.
15. **Honest answer if asked about .NET experience:** state it, then walk through the gateway and name what you'd learn first (EF migrations, Polly tuning, Identity integration).

## 9. SQL and NoSQL
1. **SQL drills (you are strong here):** window functions (ROW_NUMBER, LAG), CTEs, joins and Cartesian products, GROUP BY/HAVING, anti-joins, deduplication, indexes (B-tree, covering, composite order), EXPLAIN, isolation levels, deadlocks.
2. **Example:** latest prescription per patient: `SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY ts DESC) rn FROM rx) t WHERE rn=1;`
3. **Choosing a store.** Relational for transactions/audit/FHIR-like normalised data; DynamoDB for key-value at scale (design by access pattern, partition key choice, GSIs); document stores for flexible clinical docs; columnar (Athena/Parquet) for analytics; graph for ontologies; vector index for embeddings.
4. **Genomic data layout.** VCFs in S3, columnar variant tables (Parquet, partition by chromosome/sample), Athena/Glue, Hail/Spark for scale; HealthOmics variant stores.
5. **CAP/consistency basics, ACID vs BASE**: one sentence each.

## 10. Docker, Git, CI/CD
1. **Dockerfile best practice.** Slim base, non-root user, layer caching (copy dependency manifests first), multi-stage builds, pinned versions, `.dockerignore`, healthcheck, no secrets in layers.
2. **docker compose vs ECS/Kubernetes?** Compose for local multi-container; ECS Fargate for managed containers without servers; Kubernetes when you need its ecosystem.
3. **Git.** Branching (trunk-based vs gitflow), rebase vs merge, `git bisect`, `cherry-pick`, resolve conflicts, protect main, signed commits, conventional commits, PR reviews.
4. **CI/CD design.** Lint -> unit tests -> build -> scan (Trivy, pip-audit, dotnet list package --vulnerable) -> push -> deploy; OIDC federation for AWS instead of stored keys; environments with approvals; rollbacks by redeploying previous image tag; IaC with Terraform/CDK.
5. **Secrets.** Secrets Manager/SSM, rotated, injected at runtime; `.env` never committed (`.gitignore`).

## 11. Security, privacy, compliance
1. **Threats for this system:** broken access control, PHI leakage via logs/LLM, prompt injection, RAG poisoning, model inversion/membership inference, supply chain, over-broad IAM.
2. **Controls:** TLS everywhere, KMS at rest, private subnets/VPC endpoints, least privilege, audit trails, rate limits, input validation (pydantic `extra=forbid`), PII redaction, separation of duties, retention policies.
3. **Regulation names to know:** GDPR (special-category data, DPIA, Art. 9), HIPAA (US, for reference), Bahrain PDPL Law No. 30 of 2018, local health data rules, ISO 27001, SOC 2; ML as medical device: FDA SaMD / EU MDR; clinical safety standards (e.g., DCB0129 in the UK, IEC 62304 software lifecycle). Say "I'd confirm local requirements with the DPO/legal".
4. **De-identification limits:** genomic data cannot be truly anonymised; use controlled access and aggregation.
5. **Responsible AI in healthcare:** human in the loop, uncertainty communicated, calibration, bias audits, transparency (model card), post-market monitoring.

## 12. System design case (whiteboard)
**Prompt:** "Design a platform serving PGx predictions and a chatbot over a national genomic dataset."
Structure: clarify (users, volume, latency, data sensitivity, residency) -> data plane (S3 + KMS, ingestion, Nextflow/HealthOmics QC, normalised variant store, de-identified feature tables) -> serving (gateway, AI service, SageMaker endpoint, pgvector) -> safety (rule engine for clinical calls, guardrails, human review) -> MLOps (registry, drift, retraining, gates) -> security/governance (IAM, audit, consent, residency, DPIA) -> observability and cost -> rollout (shadow, pilot with clinicians) -> risks and open questions. Draw it and state trade-offs aloud.

## 13. Behavioural and communication
Use STAR with numbers. Prepare stories: (1) explaining a technical issue to non-technical stakeholders; (2) a pipeline failure you fixed; (3) disagreeing with a design; (4) learning a new stack fast (this project is the proof); (5) handling ambiguous requirements.
Questions to ask them: what datasets/regions are in scope; who validates clinical content; current deployment stack; how models are approved; on-call expectations; relocation/visa and local-availability terms.
Salary/availability: be factual; the post says candidates must be locally available in Bahrain.

## 14. Rapid-fire (one-liners)
- Precision vs recall? Precision = TP/(TP+FP); recall = TP/(TP+FN).
- Why cosine similarity? Direction not magnitude; equals dot product on normalised vectors.
- What is an embedding? Dense vector representing meaning for similarity search.
- Temperature 0? Near-deterministic decoding, not a guarantee of truth.
- 4xx vs 5xx? Client error vs server error; retry 5xx/429 carefully, not most 4xx.
- Idempotent? Same request repeated yields same effect.
- Hardy-Weinberg? Expected genotype frequencies p^2, 2pq, q^2 without selection/migration.
- MAF? Minor allele frequency. LD? Non-random association of alleles at nearby loci.
- Why SLCO1B1 rs4149056? Reduced-function variant (*5) linked to simvastatin myopathy risk.
- Sensitivity of CYP2C19 *17? Increased-function allele (rapid/ultrarapid).

## 15. Topic-to-code map
| Topic | Where to show it |
|---|---|
| Star alleles, phase ambiguity | `app/genomics/pgx.py`, `tests/test_pgx.py` |
| VCF parsing | `app/genomics/vcf.py` |
| ML, calibration, subgroup, drift | `app/ml/train.py`, `drift.py`, `predictor.py` |
| PyTorch | `app/ml/torch_model.py` |
| RAG, hybrid retrieval, gate | `app/rag/*`, `app/chat/service.py`, `tests/test_chat_gate_regression.py` |
| Guardrails | `app/chat/guardrails.py` |
| Bedrock | `app/rag/embeddings.py` (Titan), `app/chat/llm.py` (Converse) |
| .NET gateway | `services/gateway/src/Gateway/Program.cs`, `Audit.cs`, tests |
| Nextflow | `pipelines/nextflow/main.nf` |
| Docker/CI/AWS | `Dockerfile`s, `docker-compose.yml`, `.github/workflows`, `infra/aws` |

## 16. Study plan (14 days)
Days 1-2 PGx concepts + glossary; 3-4 re-read the repo and run it; 5-6 RAG/Bedrock hands-on (enable Bedrock, switch `GAI_EMBEDDER=bedrock`); 7 scikit-learn drills; 8-9 ASP.NET Core tutorial and build/fix the gateway locally; 10 Docker/CI; 11 SageMaker basics (deploy `scripts/deploy_sagemaker.py` in a sandbox account); 12 Nextflow tutorial; 13 mock interview + system design; 14 rehearse project script and gap answers.
