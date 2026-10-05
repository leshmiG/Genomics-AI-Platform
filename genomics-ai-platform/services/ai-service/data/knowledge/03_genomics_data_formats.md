# Genomics data formats and concepts

## Raw reads: FASTQ
FASTQ stores sequencing reads. Each read has four lines: an identifier, the base sequence, a separator and per-base quality scores in Phred scale. A Phred score of 30 means a one in a thousand chance the base call is wrong. Paired-end sequencing produces two files, R1 and R2.

## Alignment: SAM, BAM and CRAM
Reads are aligned to a reference genome with an aligner such as BWA-MEM2. SAM is the text format, BAM is the compressed binary version, and CRAM is a more compact reference-based compression. BAM and CRAM files are sorted by coordinate and indexed (.bai or .crai) so that tools can jump to a region quickly. Duplicate marking and base quality recalibration are common post-alignment steps.

## Variants: VCF and gVCF
A VCF (Variant Call Format) file lists variant sites. Header lines start with ##, the column header starts with #CHROM, and each record has CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, then FORMAT and one column per sample. The GT field is the genotype: 0 is the reference allele, 1 is the first ALT, and the separator shows phasing, with / for unphased and | for phased. A gVCF also records reference blocks, so a missing site can be distinguished from a confidently homozygous reference site. A plain VCF cannot make that distinction.

## Normalisation and annotation
Variants should be normalised, meaning left-aligned and split into biallelic records, with a tool such as bcftools norm before comparing them with databases. Annotation tools such as VEP or SnpEff add gene, consequence and population frequency information. dbSNP provides rsIDs, ClinVar provides clinical significance assertions, and gnomAD provides population allele frequencies.

## Reference builds
Coordinates depend on the reference build, for example GRCh37 (hg19) or GRCh38. The same variant has different positions in each build, so always record the build and never mix builds in one analysis. Matching by rsID avoids some build problems but not all, because rsIDs can be merged or re-mapped.

## Workflow engines
Large analyses are run as pipelines. Nextflow, Snakemake and WDL describe each step, its inputs and outputs, and the container it runs in, so runs are reproducible and can be resumed. The nf-core community maintains tested Nextflow pipelines. On AWS, AWS HealthOmics and AWS Batch can run Nextflow workflows at scale.

## Scale
A 30x human whole genome is roughly 100 GB of FASTQ and a CRAM of around 15 to 30 GB. A national cohort of tens of thousands of genomes therefore needs tiered storage, lifecycle rules, and columnar or specialised stores such as Parquet, Hail, or TileDB-VCF for query.
