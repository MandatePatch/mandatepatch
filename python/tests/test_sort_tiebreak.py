#!/usr/bin/env python3
"""Call sort_line_items directly. canonical_commitment rejects a tied triple
before the sort, so this path is the one that can observe the tie-break.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "python"))

from mandatepatch import sort_line_items  # noqa: E402


def item(title: str, amount: int) -> dict:
    return {
        "line_id": "same",
        "sku": "SKU-X",
        "variant_id": "v",
        "title": title,
        "quantity": 1,
        "unit_amount_minor": amount,
        "total_amount_minor": amount,
    }


def titles(order: str) -> list[str]:
    items = [item("A", 1), item("B", 2)] if order == "ab" else [item("B", 2), item("A", 1)]
    out = sort_line_items({"line_items": items})
    return [row["title"] for row in out["line_items"]]


def main() -> int:
    ab = titles("ab")
    ba = titles("ba")
    print(f"ab {ab}")
    print(f"ba {ba}")
    if ab != ba:
        print("FAIL  sort_line_items kept input order on a tied triple", file=sys.stderr)
        return 1
    if ab != ["A", "B"]:
        print(f"FAIL  expected ['A', 'B'], got {ab}", file=sys.stderr)
        return 1
    print("PASS  sort_line_items tie-break is independent of input order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
