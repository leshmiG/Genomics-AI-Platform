#!/usr/bin/env nextflow
nextflow.enable.dsl = 2

/*
 * VCF -> QC -> (optional) normalise -> PGx calling via the AI service.
 * Untested in the authoring sandbox (no Nextflow/Docker there); CI runs `nextflow run ... -profile test`.
 *
 *   nextflow run pipelines/nextflow -profile docker --vcf 'data/*.vcf' --ai_url http://localhost:8000
 */

params.vcf      = "${projectDir}/data/demo.vcf"
params.fasta    = null          // reference FASTA; when set, variants are left-aligned/split with bcftools norm
params.ai_url   = 'http://localhost:8000'
params.ai_key   = System.getenv('GAI_INTERNAL_API_KEY') ?: 'dev-internal-key'
params.outdir   = 'results'

process VALIDATE_AND_STATS {
    tag "$vcf.simpleName"
    container 'quay.io/biocontainers/bcftools:1.19--h8b25389_0'
    publishDir "${params.outdir}/qc", mode: 'copy'
    input:  path vcf
    output: tuple path(vcf), path("${vcf.simpleName}.stats.txt")
    script:
    """
    bcftools view -h $vcf > /dev/null          # fails fast on a malformed header
    bcftools stats $vcf > ${vcf.simpleName}.stats.txt
    """
}

process NORMALISE {
    tag "$vcf.simpleName"
    container 'quay.io/biocontainers/bcftools:1.19--h8b25389_0'
    input:  tuple path(vcf), path(stats)
            path fasta
    output: path "${vcf.simpleName}.norm.vcf"
    script:
    """
    bcftools norm -f $fasta -m -any $vcf -o ${vcf.simpleName}.norm.vcf
    """
}

process PASSTHROUGH {
    input:  tuple path(vcf), path(stats)
    output: path vcf
    script: "true"
}

process CALL_PGX {
    tag "$vcf.simpleName"
    container 'curlimages/curl:8.8.0'
    publishDir "${params.outdir}/pgx", mode: 'copy'
    input:  path vcf
    output: path "${vcf.simpleName}.pgx.json"
    script:
    """
    curl -sf -H "X-Internal-Key: ${params.ai_key}" -F file=@$vcf ${params.ai_url}/v1/pgx/from-vcf -o ${vcf.simpleName}.pgx.json
    """
}

workflow {
    vcfs = Channel.fromPath(params.vcf, checkIfExists: true)
    qc   = VALIDATE_AND_STATS(vcfs)
    ready = params.fasta ? NORMALISE(qc, file(params.fasta, checkIfExists: true)) : PASSTHROUGH(qc)
    CALL_PGX(ready)
}
