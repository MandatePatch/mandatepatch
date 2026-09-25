#!/usr/bin/env python3
"""Fail unless every schema's $id resolves, and resolves to these exact bytes.

Each schema in schemas/ declares an $id under https://mandatepatch.org/schemas/.
An $id is an identity claim: a reader who dereferences it must get this file.
The site that serves them is a separate repository, so the published copy can
drift from the source silently — this is the check that stops it.

Two assertions, in order:

  1. Offline. Each file's $id is exactly SCHEMA_BASE + the file's own name.
     Catches a rename, a copy-paste $id, and a schema added without one.
  2. Network. Each $id is fetched and its bytes must hash to this file's bytes.
     Catches the published copy lagging or diverging.

Fail-closed on purpose. If the fetch itself fails, that is a FAILURE and not a
skip: a check that quietly passes when it could not look is not a check. The
same reason the verifier in the disclosure is a total function — every
recognised failure maps to a refusal with a reason.

When this fails after a deliberate schema change, the fix is to publish the
site, not to edit this script. Order of operations: change the schema here,
copy it to the site repository, publish, then merge.

Stdlib only. Invoked from the repository root.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMA_BASE = "https://mandatepatch.org/schemas/"
TIMEOUT_S = 30

OFFLINE_ONLY = "--offline" in sys.argv


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mandatepatch-ci"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return r.read()


def main() -> int:
    files = sorted(SCHEMA_DIR.glob("*.schema.json"))
    if not files:
        print(f"FAIL  no *.schema.json under {SCHEMA_DIR.relative_to(ROOT)}")
        return 1

    failures: list[str] = []

    for path in files:
        name = path.name
        raw = path.read_bytes()

        try:
            declared = json.loads(raw)["$id"]
        except (json.JSONDecodeError, KeyError) as exc:
            failures.append(f"{name}: no readable $id ({exc})")
            continue

        expected = SCHEMA_BASE + name
        if declared != expected:
            failures.append(f"{name}: $id is {declared!r}, expected {expected!r}")
            continue

        if OFFLINE_ONLY:
            print(f"ok    {name}  $id matches (offline)")
            continue

        try:
            served = fetch(declared)
        except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
            failures.append(
                f"{name}: could not fetch {declared} ({exc}). "
                "Not a skip — an $id that cannot be dereferenced is a broken $id."
            )
            continue

        local_digest, served_digest = sha256(raw), sha256(served)
        if local_digest != served_digest:
            failures.append(
                f"{name}: served bytes differ from source.\n"
                f"        source {local_digest}  ({len(raw)} bytes)\n"
                f"        served {served_digest}  ({len(served)} bytes)\n"
                f"        Publish the site copy of this file, then merge."
            )
            continue

        print(f"ok    {name}  {local_digest[:16]}…  {len(raw)} bytes")

    if failures:
        print(f"\n{len(failures)} schema(s) failed:\n", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nThe site repository is MandatePatch/mandatepatch.org; the schemas are"
            "\nserved from its schemas/ directory.",
            file=sys.stderr,
        )
        return 1

    if OFFLINE_ONLY:
        print(f"\n{len(files)} schema(s): $id correct. Served bytes NOT checked (--offline).")
    else:
        print(f"\n{len(files)} schema(s): $id correct and served bytes identical.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
