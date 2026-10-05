#!/usr/bin/env bash
# Smoke test against a running AI service (make run) on :8000.
set -euo pipefail
H="X-Internal-Key: ${GAI_INTERNAL_API_KEY:-dev-internal-key}"
U=${AI_URL:-http://localhost:8000}
echo "--- diplotype call"; curl -s -H "$H" -H 'content-type: application/json' \
  -d '{"gene":"CYP2C19","diplotype":"*2/*2"}' $U/v1/pgx/call-diplotype; echo
echo "--- chat"; curl -s -H "$H" -H 'content-type: application/json' \
  -d '{"message":"What is a diplotype?","session_id":"demo"}' $U/v1/chat; echo
echo "--- VCF"; curl -s -H "$H" -F file=@pipelines/nextflow/data/demo.vcf $U/v1/pgx/from-vcf; echo
