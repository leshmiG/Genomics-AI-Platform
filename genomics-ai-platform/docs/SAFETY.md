# Safety, privacy and limits

- Not a medical device; educational decision-support demo. Clinical use needs validation, regulatory review and clinical governance.
- Synthetic data only. Effect sizes are invented; reported AUC says nothing about real-world performance.
- Allele tables cover 5 genes and a few alleles; real PGx needs full PharmVar/CPIC tables, structural variants (e.g. CYP2D6 copy number), and phasing.
- Guidance text is paraphrased; the source version is stamped on each response. A clinical pharmacist must sign off any production content.
- The chatbot refuses personal dosing advice, flags prompt injection, redacts PII, cites sources and refuses when ungrounded.
- Genomic data is inherently identifying and special-category under GDPR; Bahrain PDPL (Law No. 30 of 2018) also applies. Require DPIA,
  lawful basis/consent, minimisation, encryption (KMS), least privilege, audit, retention limits and a residency decision before real data.
- LLM calls: confirm region/model availability and whether cross-region inference leaves the permitted jurisdiction.
