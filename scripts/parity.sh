#!/usr/bin/env bash
# Prove that the TypeScript and Python ports of mandatepatch/profile/v1 produce
# byte-identical canonical strings, digests, and rejection codes for every shared
# test vector. Any difference is a profile bug, not a rounding difference.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/.parity"
mkdir -p "${OUT}"

echo "== building TypeScript port"
(cd "${ROOT}/ts" && npx tsc -p tsconfig.json)

echo "== TypeScript vectors"
node "${ROOT}/ts/dist/test/run-vectors.js" --emit "${OUT}/ts.json"

echo "== Python vectors"
python3 "${ROOT}/python/tests/run_vectors.py" --emit "${OUT}/py.json"

echo "== byte-for-byte comparison of the two ports' output"
if diff -u "${OUT}/ts.json" "${OUT}/py.json"; then
  echo "PASS  typescript and python produced byte-identical output"
  echo "      sha256(ts.json) = $(sha256sum "${OUT}/ts.json" | cut -d' ' -f1)"
  echo "      sha256(py.json) = $(sha256sum "${OUT}/py.json" | cut -d' ' -f1)"
else
  echo "FAIL  ports diverged; see the diff above" >&2
  exit 1
fi
