#!/usr/bin/env python3
"""Fail if README.md states a vector count other than the file's.

Counts are read from examples/canonicalization-vectors.json. The README is
scanned for the two sentence shapes that state them. There is no second list.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
doc = json.loads((ROOT / "examples" / "canonicalization-vectors.json").read_text(encoding="utf-8"))
accept = len(doc["vectors"])
reject = len(doc["rejects"])
readme = (ROOT / "README.md").read_text(encoding="utf-8")
prose = re.findall(r"(\d+) accept vectors and (\d+) reject vectors", readme)
sample = re.findall(r"(\d+) accept \+ (\d+) reject vectors", readme)
print(f"file  {accept} accept + {reject} reject")
print(f"prose {prose}")
print(f"sample {sample}")
bad = []
for n, m in prose + sample:
    if int(n) != accept or int(m) != reject:
        bad.append(f"{n} accept / {m} reject")
if not prose or not sample:
    print("FAIL  README does not state both count shapes", file=sys.stderr)
    sys.exit(1)
if bad:
    print("FAIL  README disagrees with the vector file: " + ", ".join(bad), file=sys.stderr)
    sys.exit(1)
print(f"PASS  README counts match the vector file ({accept} accept + {reject} reject)")
