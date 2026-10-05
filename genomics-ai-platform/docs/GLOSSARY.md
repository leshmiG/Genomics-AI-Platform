# Domain terminology dictionary

Grouped by area. Plain-language definitions; simplified on purpose. Verify clinical details against current guidelines.

## A. Genetics basics
- **DNA**: molecule encoding hereditary information as a sequence of bases A, C, G, T.
- **RNA / mRNA**: single-stranded copy of a gene used to make proteins.
- **Gene**: DNA segment that encodes a functional product (usually a protein).
- **Allele**: one version of a gene or variant at a locus.
- **Locus (loci)**: a position on a chromosome.
- **Chromosome**: packaged DNA; humans have 22 pairs of autosomes plus sex chromosomes (X, Y).
- **Genotype**: the alleles a person carries at a locus.
- **Phenotype**: observable trait or, in PGx, predicted drug-metabolism status.
- **Homozygous / Heterozygous / Hemizygous**: two identical alleles / two different alleles / one copy only (e.g., X in males).
- **Exon / Intron**: coding / non-coding parts of a gene. **Exome**: all exons. **Genome**: all DNA.
- **Codon**: three bases coding one amino acid. **Missense / Nonsense / Synonymous / Frameshift**: amino-acid change / premature stop / silent change / indel shifting the reading frame.
- **Splice site**: boundary where introns are removed; variants here can disrupt RNA processing.
- **Promoter / Enhancer / UTR**: regulatory regions controlling expression.
- **Haplotype**: set of variants inherited together on one chromosome copy.
- **Diplotype**: the pair of haplotypes in an individual (e.g., *1/*2).
- **Phasing**: determining which variants lie on the same chromosome copy. **cis / trans**: same / different copy.
- **Linkage disequilibrium (LD)**: non-random association of nearby alleles.
- **Hardy-Weinberg equilibrium (HWE)**: expected genotype frequencies p², 2pq, q²; deviations flag QC issues or selection.
- **Allele frequency (AF) / Minor allele frequency (MAF)**: how common an allele is in a population / the less common allele's frequency.
- **De novo variant**: new in the child, absent in parents. **Penetrance**: chance a carrier shows the trait. **Expressivity**: severity range.
- **Mendelian inheritance (autosomal dominant/recessive, X-linked)**: patterns of transmission.
- **Consanguinity**: parents related by ancestry; raises recessive-disease rates (relevant in Gulf populations).
- **Founder effect / Population stratification**: variants common in a group from small founding populations / ancestry differences that confound association.
- **Epigenetics / Methylation**: heritable regulation without sequence change.
- **Mitochondrial DNA**: maternally inherited circular genome.

## B. Variants
- **Variant / Mutation / Polymorphism**: difference from reference; "polymorphism" usually means common (>1%).
- **SNP / SNV**: single-nucleotide polymorphism / variant. **rsID**: dbSNP identifier (e.g., rs4244285).
- **Indel**: insertion or deletion. **MNV**: multi-nucleotide variant.
- **CNV (copy-number variant)**: deletion/duplication of larger segments (central to CYP2D6).
- **SV (structural variant)**: large rearrangements: inversions, translocations.
- **STR / Repeat expansion**: short tandem repeats; expansions cause some diseases.
- **Multi-allelic site**: more than one ALT allele at a position. **Left-alignment / normalisation**: canonical representation of indels.
- **REF / ALT**: reference / alternate allele in VCF. **QUAL, FILTER, INFO, FORMAT, GT, DP, GQ, AD, PL**: VCF fields (quality, filter status, annotations, per-sample format, genotype, depth, genotype quality, allele depth, phred-scaled likelihoods).
- **Phred score**: Q = -10 log10(error probability); Q30 = 1 in 1000 error.
- **HGVS**: standard variant nomenclature (c. coding, p. protein, g. genomic), e.g., NM_000769.4:c.681G>A.
- **VUS**: variant of uncertain significance. **ClinVar**: public archive of variant interpretations. **gnomAD**: aggregated population allele frequencies. **dbSNP**: variant ID database.
- **ACMG/AMP**: five-tier classification: Pathogenic, Likely pathogenic, VUS, Likely benign, Benign. **Pathogenic**: causes disease.
- **LoF (loss of function)**: variant abolishing gene function. **Gain of function**: increased/novel activity.
- **Zygosity / Allelic balance**: copy count / ratio of reads for ALT vs REF.
- **Mosaicism**: different genotypes in different cells of one person. **Somatic vs germline**: acquired (tumour) vs inherited.
- **GWAS / PRS**: genome-wide association study / polygenic risk score.
- **eQTL**: variant associated with expression level. **Fine-mapping**: identifying the causal variant in an associated region.

## C. Sequencing and bioinformatics
- **NGS (next-generation sequencing)**: high-throughput sequencing. **Short-read (Illumina) / Long-read (PacBio, Oxford Nanopore)**: ~150 bp vs kb-length reads; long reads help phasing and SVs.
- **WGS / WES / Panel / Genotyping array**: whole genome / exome / targeted genes / chip for known SNPs (imputation fills the rest).
- **Read / Coverage (depth) / Breadth**: sequence fragment / average reads covering a base / fraction covered at a depth.
- **Paired-end**: reads from both fragment ends. **Adapter trimming**: remove library adapters.
- **FASTA / FASTQ / SAM / BAM / CRAM / VCF / gVCF / BED / GFF/GTF / BCF**: sequence / reads+quality / alignments text / binary / compressed alignments / variants / variants with reference blocks / regions / annotations / binary VCF.
- **Reference genome / GRCh37 (hg19) / GRCh38 (hg38) / T2T-CHM13**: assembly versions; coordinates differ across builds. **Liftover**: converting coordinates.
- **Alignment / Mapping / MAPQ**: placing reads on the reference / mapping quality. **BWA-MEM2, minimap2**: aligners.
- **Duplicate marking / BQSR**: flag PCR duplicates / recalibrate base qualities.
- **Variant calling**: inferring variants from alignments. **GATK HaplotypeCaller, DeepVariant, bcftools mpileup/call, FreeBayes**: callers. **Joint genotyping**: calling across a cohort together.
- **Hard filtering / VQSR**: threshold-based / model-based variant filtering.
- **Annotation**: adding gene/effect/frequency. **VEP, ANNOVAR, SnpEff**: annotators. **SIFT, PolyPhen, CADD, REVEL**: deleteriousness predictors.
- **bcftools / samtools / bedtools / htslib / tabix**: core command-line tools (tabix indexes bgzipped files).
- **bgzip / .tbi / .csi**: block-gzip and index files for random access.
- **FastQC / MultiQC**: read QC reports.
- **Ti/Tv ratio**: transition/transversion ratio, QC metric (~2.0-2.1 WGS).
- **Contamination / Sample swap / Concordance**: QC checks (VerifyBamID, sex check, relatedness).
- **Pipeline / Workflow manager**: **Nextflow, Snakemake, WDL/Cromwell, CWL**; **nf-core**: curated Nextflow pipelines.
- **Nextflow terms**: process, channel, operator, workflow, profile, `-resume`, work directory, `publishDir`, executor (local, slurm, awsbatch).
- **Container / Singularity / Apptainer / BioContainers**: packaging tools reproducibly; Singularity common on HPC.
- **HPC / Slurm**: high-performance computing / job scheduler.
- **GA4GH**: Global Alliance for Genomics and Health: standards (htsget, Beacon, Phenopackets, VRS, DRS, WES/TES, Passports).
- **Hail / Glow / Spark**: scalable genomics analytics.
- **Imputation / Reference panel (TOPMed, HRC)**: infer ungenotyped variants.
- **Joint calling vs single-sample calling; gVCF workflow**: scalable cohort calling.
- **Provenance**: recorded tool versions, parameters, reference, containers.

## D. Pharmacogenomics (PGx)
- **Pharmacogenomics / Pharmacogenetics**: study of how genes (genome-wide / single gene) affect drug response.
- **Pharmacokinetics (PK) / Pharmacodynamics (PD)**: what the body does to the drug / what the drug does to the body.
- **ADME**: absorption, distribution, metabolism, excretion.
- **Prodrug / Active metabolite**: inactive drug activated by metabolism (clopidogrel, codeine, tamoxifen).
- **CYP450 (CYP2C19, CYP2C9, CYP2D6, CYP3A4/5, CYP1A2)**: liver enzyme family metabolising many drugs.
- **Phase I / Phase II enzymes**: oxidation etc. / conjugation (TPMT, UGT1A1, NAT2).
- **Transporters (SLCO1B1, ABCB1, ABCG2)**: move drugs across membranes.
- **HLA (HLA-B*57:01, HLA-B*15:02, HLA-A*31:01)**: immune genes linked to hypersensitivity (abacavir, carbamazepine).
- **VKORC1**: warfarin target gene. **DPYD**: fluoropyrimidine metabolism. **TPMT / NUDT15**: thiopurine metabolism. **UGT1A1**: irinotecan/ atazanavir. **G6PD**: deficiency causes haemolysis with some drugs (rasburicase, primaquine); relevant in the Gulf. **RYR1/CACNA1S**: malignant hyperthermia. **IFNL3**, **CFTR**, **MT-RNR1** (aminoglycoside ototoxicity), **F5**.
- **Star (*) allele**: named haplotype (e.g., CYP2C19*2). ***1**: reference/normal-function by convention (may not mean no variants).
- **Diplotype → Phenotype**: translation using allele function.
- **Function categories**: no function, decreased function, normal function, increased function.
- **Activity score (AS)**: numerical sum of allele values (e.g., DPYD, CYP2C9, CYP2D6).
- **Metabolizer phenotypes**: Ultrarapid (UM), Rapid (RM), Normal (NM), Intermediate (IM), Poor (PM). Transporter labels: Normal/Decreased/Poor function.
- **Actionable gene-drug pair**: guideline recommends a change based on genotype.
- **CPIC**: Clinical Pharmacogenetics Implementation Consortium (guidelines, allele tables). **DPWG**: Dutch Pharmacogenetics Working Group. **PharmGKB**: knowledge base; **PharmVar**: star-allele nomenclature; **CPIC levels / PharmGKB levels of evidence**: A-D / 1A-4.
- **FDA table of pharmacogenomic biomarkers**; **EMA SmPC**: labels mentioning PGx.
- **Preemptive vs reactive testing**: test in advance and store results / test when a drug is prescribed.
- **Clinical decision support (CDS)**: software alerting clinicians at prescribing time. **Pharmacist review**: clinical sign-off role.
- **Therapeutic drug monitoring (TDM)**: measure drug levels. **INR**: warfarin monitoring measure. **ACS / PCI**: acute coronary syndrome / percutaneous coronary intervention (clopidogrel context). **Myopathy / rhabdomyolysis**: statin muscle toxicity. **Myelosuppression**: bone-marrow suppression (thiopurines, fluoropyrimidines).
- **Adverse drug reaction (ADR) / Drug-drug interaction (DDI) / Phenoconversion**: harm from a drug / interaction / drug-induced change of apparent phenotype (e.g., CYP2D6 inhibitors).
- **Indeterminate / No call**: result that cannot be assigned (e.g., ambiguous phase or uncalled variants).
- **Structural PGx**: copy-number/hybrid alleles; tools Stargazer, Aldy, Cyrius, PharmCAT (CPIC-aligned caller), PyPGx.
- **Clinical validity vs clinical utility vs analytical validity**: association strength / improves outcomes / test accuracy.

## E. Clinical data and healthcare IT
- **EHR / EMR**: electronic health/medical record. **PHI**: protected health information. **PII**: personally identifiable information. **MRN**: medical record number.
- **HL7 v2**: legacy message standard. **HL7 FHIR**: modern REST/JSON health data standard; resources: Patient, Observation, MedicationRequest, DiagnosticReport, Condition; **FHIR Genomics Reporting IG**.
- **OMOP CDM / OHDSI**: common data model for observational research. **i2b2, TriNetX**: cohort platforms.
- **LOINC / SNOMED CT / ICD-10 / RxNorm / ATC / HPO / MONDO**: lab codes / clinical terms / diagnoses / drug names / drug classes / phenotype ontology / disease ontology.
- **DICOM / PACS**: imaging standard / archive. **LIMS**: laboratory information management system. **CDS Hooks / SMART on FHIR**: EHR integration standards.
- **Cohort / Biobank / Registry / Longitudinal data**: defined study group / sample+data repository / disease or exposure register / repeated measures.
- **Case-control / Cohort study / RCT / Real-world evidence (RWE)**: study designs.
- **Phenotyping algorithm**: rules identifying disease status from EHR.
- **eGFR / BMI / HbA1c / INR**: kidney function, body mass index, glycaemic control, clotting measure (common features).
- **Sensitivity / Specificity / PPV / NPV**: diagnostic accuracy measures.
- **Informed consent / Broad consent / Dynamic consent**: permission models for data use.
- **IRB / Ethics committee**: research ethics review. **DPIA**: data protection impact assessment. **DPO**: data protection officer. **Controlled access / Data Access Committee (DAC)**: gatekeeping of genomic data.
- **De-identification / Pseudonymisation / Anonymisation / k-anonymity**: removing identifiers / replacing with codes (reversible) / irreversible / group-size privacy measure.
- **Federated learning / Trusted Research Environment (TRE) / Secure enclave**: compute-to-data approaches.
- **GDPR (Art. 9 special category), HIPAA, Bahrain PDPL (Law No. 30 of 2018), SaMD (FDA), MDR (EU), IEC 62304, ISO 13485, ISO 27001, CAP/CLIA/ISO 15189**: regulations/standards for data, devices, software lifecycle, quality, and labs.
- **National genome programmes**: population-scale sequencing initiatives (e.g., Bahrain Genome Project, Emirati Genome Programme, Saudi Genome Program, Genomics England).

## F. Machine learning
- **Supervised / Unsupervised / Semi-supervised / Self-supervised**: labelled / unlabelled / mixed / labels from data itself.
- **Features / Label / Target / Cohort / Train-validation-test split**.
- **Overfitting / Underfitting / Bias-variance trade-off / Regularisation (L1, L2) / Early stopping / Dropout**.
- **Data leakage / Target leakage / Train-serve skew**.
- **Cross-validation (k-fold, stratified, group, nested) / Hyperparameter tuning (grid, random, Bayesian)**.
- **Logistic regression, Random forest, Gradient boosting (XGBoost, LightGBM, HistGradientBoosting), SVM, kNN, Naive Bayes, MLP, CNN, RNN/LSTM, Transformer**.
- **Metrics**: accuracy, precision, recall, F1, ROC-AUC, PR-AUC, log loss, **Brier score**, RMSE, MAE, calibration, **ECE (expected calibration error)**, reliability diagram, decision-curve analysis, net benefit.
- **Calibration (Platt/sigmoid, isotonic)**: aligning predicted probabilities with observed frequencies.
- **Class imbalance / SMOTE / class weights / threshold tuning**.
- **Subgroup analysis / Fairness / Equalised odds / Calibration within groups**.
- **Explainability**: coefficients, permutation importance, **SHAP**, LIME, partial dependence, occlusion.
- **Drift: data / concept / label shift; PSI (population stability index; 0.1 warn, 0.25 act); KS test; Jensen-Shannon**.
- **Model card / Datasheet / Model registry / Experiment tracking (MLflow, SageMaker Experiments)**.
- **Pipeline (scikit-learn) / ColumnTransformer / OneHotEncoder / StandardScaler / SimpleImputer / joblib**.
- **Tensor / Autograd / Gradient descent / Adam(W) / Batch size / Epoch / Learning rate / Backpropagation / Loss function / Logits / Softmax / Sigmoid / ReLU / Batch normalisation**.
- **PyTorch (nn.Module, DataLoader, torch.save/state_dict, TorchScript), TensorFlow/Keras (SavedModel, tf.function, tf.data), ONNX**.
- **Transfer learning / Fine-tuning / Embeddings / Foundation model**.
- **Genomic models**: DeepVariant, AlphaFold/AlphaMissense (variant effect), Enformer, DNA language models (Nucleotide Transformer, Evo).
- **Synthetic data**: simulated data used here; useful for testing, never evidence of clinical performance.

## G. LLMs, RAG and vector search
- **LLM / Token / Context window / Temperature / Top-p / System prompt / Few-shot / Chain of thought**.
- **Hallucination / Grounding / Faithfulness / Citation / Refusal / Abstention**.
- **RAG (retrieval-augmented generation)**: retrieve evidence then generate an answer from it.
- **Chunking / Overlap / Metadata filtering / Reranking / Query rewriting / HyDE / Multi-query**.
- **Embedding / Cosine similarity / Dot product / Euclidean distance / Dimension / Normalisation**.
- **Vector database / Vector index / ANN (approximate nearest neighbour) / HNSW / IVF / Flat / PQ (product quantisation) / Recall@k**.
- **pgvector, OpenSearch k-NN, Pinecone, Weaviate, Qdrant, Milvus, FAISS, Chroma, Bedrock Knowledge Bases**.
- **BM25 / TF-IDF / Sparse retrieval / Dense retrieval / Hybrid search / Reciprocal Rank Fusion (RRF)**.
- **Grounding gate**: threshold check deciding whether retrieved evidence suffices to answer.
- **Prompt injection (direct/indirect) / Jailbreak / RAG poisoning / Data exfiltration / PII redaction / Guardrails / Red-teaming**.
- **Tool use / Function calling / Agent / ReAct / MCP (Model Context Protocol) / LangChain / LangGraph / LlamaIndex**.
- **Evaluation**: recall@k, MRR, nDCG, RAGAS, LLM-as-judge, golden set, regression suite.
- **Fine-tuning / LoRA / RLHF / Distillation / Quantisation**.
- **Bedrock terms**: Converse API, InvokeModel, model access, inference profile (cross-region), Guardrails (denied topics, word/PII filters, contextual grounding), Knowledge Bases, Agents for Bedrock, Titan Text Embeddings, Provisioned Throughput.

## H. MLOps and AWS
- **MLOps / CI/CD / CT (continuous training) / Model monitoring / Canary / Blue-green / Shadow deployment / Rollback / A/B test**.
- **Amazon S3, KMS, IAM (role, policy, least privilege), STS, VPC, subnet, security group, VPC endpoint (PrivateLink), NAT, CloudWatch, CloudTrail, Secrets Manager, SSM Parameter Store, ECR, ECS/Fargate, EKS, Lambda, API Gateway, ALB, WAF, Cognito, Step Functions, SQS/SNS/EventBridge, DynamoDB, RDS/Aurora, Athena, Glue, Lake Formation, Macie**.
- **SageMaker**: Studio, Processing, Training jobs, Experiments, Pipelines, Model Registry, Endpoints (real-time/serverless/async/multi-model), Batch Transform, Feature Store, Model Monitor, Clarify (bias/explainability), Ground Truth, JumpStart.
- **AWS HealthOmics**: managed genomics storage (sequence/reference/variant/annotation stores) and workflows (Nextflow/WDL/CWL). **AWS Batch**: container batch compute (used by Nextflow). **AWS HealthLake**: FHIR store. **Amazon Comprehend Medical**: clinical NLP.
- **IaC / Terraform / CloudFormation / CDK**. **OIDC federation**: GitHub Actions assume AWS roles without keys.
- **Data residency / Data sovereignty / Region (me-south-1 Bahrain, me-central-1 UAE, eu-central-1 Frankfurt)**: where data may live and be processed.
- **SLO / SLI / SLA, p95 latency, RPS, Prometheus, Grafana, OpenTelemetry, structured logging, correlation/request ID**.

## I. .NET and integration
- **ASP.NET Core / Kestrel / Minimal API / Controller / Middleware / Routing / Model binding / Filters**.
- **Dependency injection (Singleton/Scoped/Transient) / Options pattern / IConfiguration / User secrets**.
- **Authentication (JWT bearer, OIDC, OAuth 2.0) / Authorisation (roles, claims, policies) / CORS / Antiforgery / Rate limiting**.
- **EF Core / DbContext / Migrations / LINQ / Change tracking / AsNoTracking / Dapper / ADO.NET**.
- **HttpClientFactory / Typed client / Polly / Resilience pipeline (retry, circuit breaker, timeout, hedging, bulkhead)**.
- **Health checks / Swagger-OpenAPI / Problem Details (RFC 7807) / gRPC / SignalR / Background services / IHostedService**.
- **xUnit / WebApplicationFactory / Moq / Testcontainers**.
- **REST / HTTP verbs and status codes / Idempotency key / Pagination / Versioning / HATEOAS**.
- **Microservices / API gateway / BFF (backend-for-frontend) / Service discovery / Saga / Outbox / CQRS / Event sourcing / Circuit breaker / Bulkhead / Sidecar / Distributed tracing**.
- **SQL vs NoSQL / ACID / BASE / CAP / Index / Transaction isolation / Sharding / Replication**.
- **Docker: image, container, layer, Dockerfile, multi-stage build, registry, volume, network, compose**. **Git: commit, branch, merge, rebase, cherry-pick, tag, PR, trunk-based development**.
