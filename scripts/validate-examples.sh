#!/usr/bin/env bash
# Validate every example instance against its JSON Schema (draft 2020-12).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pairs=(
  "canonical-commitment.schema.json:canonical-commitment.example.json"
  "mandate.schema.json:mandate.example.json"
  "mandate-patch.schema.json:mandate-patch.example.json"
  "divergence-record.schema.json:divergence-record.example.json"
  "supersession-record.schema.json:supersession-record.example.json"
)

status=0
for pair in "${pairs[@]}"; do
  schema="${ROOT}/schemas/${pair%%:*}"
  instance="${ROOT}/examples/${pair##*:}"
  if npx --yes ajv-cli@5 validate --spec=draft2020 --strict=false -c ajv-formats -s "${schema}" -d "${instance}"; then
    :
  else
    status=1
  fi
done
exit "${status}"
