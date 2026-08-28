#!/usr/bin/env python3
"""Fail if the three declared package versions disagree.

Sources (exactly three — do not add a fourth):
  python/pyproject.toml              [project].version
  ts/package.json                    version
  python/mandatepatch/__init__.py    __version__

Stdlib only (tomllib is in 3.11). Invoked from the repository root.
A checker that is committed but never run is not a check.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pyproject_version() -> str:
    data = tomllib.loads((ROOT / "python" / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def package_json_version() -> str:
    data = json.loads((ROOT / "ts" / "package.json").read_text(encoding="utf-8"))
    return str(data["version"])


def init_version() -> str:
    text = (ROOT / "python" / "mandatepatch" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', text, re.M)
    if match is None:
        raise SystemExit("FAIL  __version__ not found in python/mandatepatch/__init__.py")
    return match.group(1)


def main() -> int:
    declared = {
        "python/pyproject.toml": pyproject_version(),
        "ts/package.json": package_json_version(),
        "python/mandatepatch/__init__.py": init_version(),
    }
    distinct = sorted(set(declared.values()))
    for path, version in declared.items():
        print(f"  {version}  {path}")
    if len(distinct) != 1:
        print(
            f"FAIL  {len(distinct)} distinct versions declared: {', '.join(distinct)}",
            file=sys.stderr,
        )
        return 1
    print(f"PASS  all three sources declare {distinct[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
