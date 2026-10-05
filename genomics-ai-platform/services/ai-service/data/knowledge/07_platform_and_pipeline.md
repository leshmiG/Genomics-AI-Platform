# About this platform and its pipeline

## Architecture overview
The platform has three runtime parts. A .NET gateway authenticates users with JWT, applies rate limits and writes an audit trail. A Python AI service performs PGx calling, risk prediction and retrieval-augmented chat. A Nextflow pipeline prepares VCF files for the AI service. PostgreSQL with the pgvector extension can store embeddings for production, while the default in-memory store lets the project run with no external services.

## How the chatbot answers
The chatbot never computes a clinical call with a language model. When a message contains a gene and diplotype, a deterministic tool translates it to a phenotype and attaches the guidance table entry. For general questions, the service retrieves the best matching passages from the knowledge base using dense vector search and BM25 keyword search fused with reciprocal rank fusion. If no passage is similar enough, the bot says that it does not know instead of guessing. Every answer lists numbered sources.

## Safety behaviours
The service redacts obvious identifiers such as emails, phone numbers and national ID numbers before processing, refuses prompt-injection attempts, declines personal dosing instructions and directs users to their clinician. Responses that discuss drug therapy include a disclaimer.

## Nextflow pipeline stages
The demonstration workflow validates the input VCF, normalises it with bcftools, subsets it to the pharmacogene target regions, produces a QC summary with variant counts, and then calls the AI service to produce a PGx report per sample. Each step runs in its own container, and the workflow can be resumed after failure with the resume option.

## Model lifecycle
A training script builds the model from a synthetic cohort, calibrates it, evaluates it per subgroup, and writes a model card. CI trains the model, runs the tests and builds container images. The service exposes the model version and a drift endpoint that compares a batch of inputs with the training reference.

## Deployment targets
Containers can run on Amazon ECS on Fargate, Amazon EKS, or any Docker host. The infra folder contains example Terraform for a small ECS service with a private network, and notes for deploying the model to a SageMaker endpoint if independent scaling or a managed model registry is needed.
