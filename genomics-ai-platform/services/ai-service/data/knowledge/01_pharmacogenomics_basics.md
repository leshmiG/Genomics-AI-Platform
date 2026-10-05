# Pharmacogenomics basics

## What pharmacogenomics studies
Pharmacogenomics (PGx) studies how inherited DNA variation changes the way a person absorbs, metabolizes, transports or responds to a drug. The goal is to pick the right drug and dose for the right patient and to avoid predictable adverse reactions. It is a subset of precision medicine and is closely related to pharmacogenetics, which traditionally refers to single-gene effects.

## Star alleles, haplotypes and diplotypes
Many pharmacogenes are described with star (*) allele nomenclature. A star allele is a named haplotype, meaning a set of variants inherited together on one copy of a chromosome. The reference or wild-type haplotype is usually called *1. A diplotype combines the two haplotypes a person carries, for example CYP2C19 *1/*2. Allele definitions are curated by PharmVar, and the clinical meaning of each allele is curated by CPIC and PharmGKB.

## From genotype to phenotype
The translation chain is genotype (the variants observed), then diplotype (the two star alleles), then phenotype (the predicted functional category), then a gene-drug recommendation. Typical metabolizer categories are ultrarapid, rapid, normal, intermediate and poor metabolizer. Some genes use an activity score: each allele gets a value such as 1.0 for normal function, 0.5 for decreased function and 0 for no function, and the two values are summed to get the diplotype activity score. Transporter genes such as SLCO1B1 use function labels instead, for example normal, decreased or poor function.

## Why phase matters
Genotype calls from short-read sequencing are often unphased. If a person is heterozygous at two variants in the same gene, the variants may sit on the same chromosome copy (cis) or on different copies (trans). For TPMT, being heterozygous at both *3B and *3C defining variants means either one *3A haplotype (intermediate metabolizer) if they are in cis, or a *3B/*3C pair (poor metabolizer) if they are in trans. Software must either use phased data or report the result as indeterminate rather than guessing.

## Limits of PGx predictions
A phenotype is a prediction, not a measurement. Other factors also change drug response: age, kidney and liver function, drug-drug interactions, adherence, and variants that the assay did not test. Structural variation such as gene deletions or duplications (important for CYP2D6) needs specialised methods and cannot be seen from a simple list of single-nucleotide variants.

## Key institutions
CPIC (Clinical Pharmacogenetics Implementation Consortium) publishes peer-reviewed, gene-drug guidelines. DPWG is the Dutch Pharmacogenetics Working Group. PharmGKB is a curated knowledge base of gene-drug annotations. PharmVar maintains the star allele definitions. FDA drug labels also contain pharmacogenomic information.
