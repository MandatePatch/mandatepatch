#!/usr/bin/env python3
"""Validate every accept vector whose mode is commitment against the
canonical-commitment schema. The mode field in the vector file is the
discriminator. There is no separate list of names.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "examples" / "canonicalization-vectors.json"
SCHEMA = ROOT / "schemas" / "canonical-commitment.schema.json"


def main() -> int:
    doc = json.loads(VECTORS.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    failures = 0
    checked = 0
    for item in doc["vectors"]:
        if item.get("mode") != "commitment":
            continue
        checked += 1
        errors = list(validator.iter_errors(item["input"]))
        if errors:
            failures += 1
            print(f"FAIL {item['name']}")
            for err in errors:
                print(f"  {err.message}")
        else:
            print(f"PASS {item['name']}")
    if failures:
        print(f"FAIL  {failures} of {checked} commitment accept vectors rejected", file=sys.stderr)
        return 1
    print(f"PASS  {checked} commitment accept vectors validate against canonical-commitment.schema.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
