#!/usr/bin/env python3
"""Assert that each signed artifact's ds_tag is recomputable from the artifact alone.

Derives the tag using only values read from the example file: the six
domain_separation members plus the top-level binding_profile. Must not import
any constant from build-examples.py or either port.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    "mandate.example.json",
    "mandate-patch.example.json",
    "divergence-record.example.json",
    "supersession-record.example.json",
]


def _lp(x: str) -> bytes:
    b = str(x).encode("utf-8")
    return len(b).to_bytes(2, "big") + b


def _b64u(raw: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def derive(sep: dict, binding_profile: str) -> str:
    buf = b"MandateLifecycle/v1/transcript"
    for key in ("purpose", "audience", "relying_party", "mandate_family_id", "mandate_version", "rail"):
        buf += _lp(sep[key])
    buf += _lp(binding_profile)
    return _b64u(hashlib.sha256(buf).digest())


def main() -> int:
    failures = []
    passes = 0
    for name in EXAMPLES:
        path = ROOT / "examples" / name
        data = json.loads(path.read_text(encoding="utf-8"))
        sig = data.get("human_signature") or data.get("signature")
        if sig is None:
            failures.append(f"{name}: no signature object")
            continue
        expected = sig.get("ds_tag")
        sep = sig.get("domain_separation")
        if sep is None or expected is None:
            failures.append(f"{name}: missing domain_separation or ds_tag")
            continue
        bp = data.get("binding_profile")
        if bp is None:
            failures.append(f"{name}: missing top-level binding_profile (cannot recompute from file alone)")
            continue
        actual = derive(sep, bp)
        if actual != expected:
            failures.append(f"{name}: ds_tag mismatch\n  expected {expected}\n  derived  {actual}")
        else:
            passes += 1
            print(f"PASS  {name}")
    if failures:
        print(f"\n{len(failures)} fail(s), {passes} pass(es):", file=sys.stderr)
        for f in failures:
            print(f"  FAIL  {f}", file=sys.stderr)
        return 1
    print(f"\nPASS  {passes}/{len(EXAMPLES)} examples recomputable from the file alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
