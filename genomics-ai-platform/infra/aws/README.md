# AWS deployment notes

**Not applied in the authoring sandbox.** Review every resource and region before use.

## Topology
- ECR: `ai-service`, `gateway` images (scan on push).
- ECS Fargate in **private subnets**; ALB (TLS, WAF) -> gateway only. The AI service has no public listener.
- Secrets Manager: `GAI_INTERNAL_API_KEY`, `Jwt__SigningKey`, DB credentials (never plain env in task defs).
- RDS PostgreSQL + pgvector (`CREATE EXTENSION vector;`), KMS-encrypted, Multi-AZ.
- VPC endpoints: `bedrock-runtime`, `ecr.api/dkr`, `s3`, `secretsmanager`, `logs`; no NAT egress for PHI paths.
- S3 (KMS, versioned, block public access) for VCFs; Nextflow work dir on S3; AWS Batch or AWS HealthOmics for pipelines.
- CloudTrail + CloudWatch alarms (5xx, latency, drift alert metric).

## Bedrock and data residency
Confirm that the chosen model and embedding model are available in your region (Bahrain is `me-south-1`;
many Bedrock models are not offered there). Cross-region inference profiles can route requests to other regions, which may
conflict with data-residency rules (Bahrain PDPL). Decide with legal/DPO before enabling; send only de-identified,
redacted text to the LLM (the chat service already redacts PII).

## SageMaker option
Package `artifacts/models/*.joblib` in a SageMaker inference container (or use a SKLearn model + `inference.py`), deploy
with `scripts/deploy_sagemaker.py`, register in Model Registry with the model card, and gate promotion on the
metrics/ECE/subgroup thresholds.

## IAM (least privilege)
Task role: `bedrock:InvokeModel` on specific model ARNs, `secretsmanager:GetSecretValue` on specific secrets, S3 read on one prefix.
