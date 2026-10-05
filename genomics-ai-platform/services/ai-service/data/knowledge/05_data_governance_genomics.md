# Data governance and privacy for genomic data

## Genomic data is inherently identifying
A genome is a unique and permanent identifier and it also reveals information about relatives. Removing names does not make genomic data anonymous, because genotype data can be linked back to individuals using public genealogy databases or surname inference. Systems should therefore treat even de-identified genomic data as sensitive, use controlled access, and avoid releasing individual-level data openly.

## Legal and regulatory context
Rules differ by country. Examples include the EU General Data Protection Regulation (GDPR), which classifies genetic data as a special category, HIPAA in the United States, and national laws such as Bahrain's Personal Data Protection Law (Law No. 30 of 2018), which also imposes obligations around sensitive personal data. Check requirements for consent, purpose limitation, cross-border transfer, retention and breach notification with legal counsel for each deployment.

## Technical controls
Core controls include encryption in transit with TLS and at rest with KMS-managed keys, least-privilege IAM roles, network isolation with private subnets and VPC endpoints, per-request audit logs that record who accessed which record and why, and separate environments for development and production. Developers should use synthetic data wherever possible. Secrets belong in a secrets manager, not in code or environment files committed to Git.

## Data residency
National genomic datasets are often required to stay within the country or region. Choose cloud regions, model-hosting options and logging destinations accordingly, and confirm that managed AI services process data in an approved region. Cross-region inference profiles can move data across regions, so check the service documentation before enabling them.

## Consent and governance
Consent should specify allowed uses, such as clinical care, research or commercial use, and participants should be able to withdraw. A data access committee reviews requests for secondary use. Provenance records link every derived dataset or model to the data and consent scope that produced it.

## Logging without leaking
Application logs must not contain patient identifiers, genotypes or free-text clinical notes. Log request identifiers, timings, model versions and pseudonymous subject keys instead. Chatbot transcripts need the same protection as clinical records and should have a short retention period.
