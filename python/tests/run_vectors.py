#!/usr/bin/env python3
"""Recompute every vector in examples/canonicalization-vectors.json, assert the
frozen expected values byte for byte, and emit this port's computed output so the
CI parity job can diff it against the TypeScript port's.

Usage: python3 python/tests/run_vectors.py [--emit <path>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "python"))

from mandatepatch.canonicalize import (  # noqa: E402
    CanonicalizationError,
    canonical_commitment,
    canonicalize,
    digest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit")
    args = parser.parse_args()

    path = os.path.join(ROOT, "examples", "canonicalization-vectors.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)

    computed = []
    failures = []

    for v in doc["vectors"]:
        if v["mode"] == "commitment":
            out = canonical_commitment(v["input"])
            jcs, dg = out["canonical"], out["digest"]
        else:
            jcs, dg = canonicalize(v["input"]), digest(v["input"])
        computed.append({"name": v["name"], "jcs": jcs, "digest": dg})
        if jcs != v["expected_jcs"]:
            failures.append(
                f"{v['name']}: jcs mismatch\n"
                f"  expected {json.dumps(v['expected_jcs'])}\n"
                f"  actual   {json.dumps(jcs)}"
            )
        if dg != v["expected_digest"]:
            failures.append(
                f"{v['name']}: digest mismatch\n"
                f"  expected {v['expected_digest']}\n  actual   {dg}"
            )

    for r in doc["rejects"]:
        code = "<no error raised>"
        try:
            canonical_commitment(r["input"]) if r["mode"] == "commitment" else canonicalize(r["input"])
        except CanonicalizationError as exc:
            code = exc.code
        except Exception as exc:  # noqa: BLE001
            code = f"<{type(exc).__name__}>"
        computed.append({"name": r["name"], "error_code": code})
        if code != r["expected_error_code"]:
            failures.append(
                f"{r['name']}: error mismatch\n"
                f"  expected {r['expected_error_code']}\n  actual   {code}"
            )

    if args.emit:
        with open(args.emit, "w", encoding="utf-8") as fh:
            json.dump(computed, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    total = len(doc["vectors"]) + len(doc["rejects"])
    if failures:
        print(f"FAIL  python: {len(failures)} of {total} vectors mismatched", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        return 1
    print(
        f"PASS  python: {len(doc['vectors'])} accept + {len(doc['rejects'])} reject vectors, "
        f"profile {doc['profile']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
