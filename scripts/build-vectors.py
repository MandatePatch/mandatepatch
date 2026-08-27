#!/usr/bin/env python3
"""Regenerate examples/canonicalization-vectors.json.

The vectors are the contract between the TypeScript and Python ports: both CI jobs
recompute every vector and assert byte-identical output against the frozen
expected values in this file, and the parity job diffs the two ports' computed
output directly. Run this only when deliberately changing profile v1.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

from mandatepatch.canonicalize import (  # noqa: E402
    CanonicalizationError,
    DEFAULT_PROFILE_ID,
    canonical_commitment,
    canonicalize,
    digest,
)

CART = json.load(
    open(os.path.join(ROOT, "examples", "canonical-commitment.example.json"), encoding="utf-8")
)
REVERSED_CART = dict(CART)
REVERSED_CART["line_items"] = list(reversed(CART["line_items"]))

# v2.3 erratum (§4.3): the per-attempt distinguisher. Identical in every other field
# to CART - same seller, same line items, same totals, same checkout_id - so the only
# thing that can move the digest is attempt_nonce itself.
RE_PRESENTED_CART = dict(CART)
RE_PRESENTED_CART["attempt_nonce"] = "Y2hMd18wUXZOZTdrUmpEcVM"

ACCEPT = [
    (
        "empty-object",
        "value",
        {},
        "The base case: SHA-256 over the two bytes '{}'.",
    ),
    (
        "nulls-booleans-empty-containers",
        "value",
        {"a": None, "b": True, "c": False, "d": [], "e": {}},
        "Explicit null is a value, not an omission. Profile v1 requires explicit null over "
        "omission throughout the 4.3 schema so that 'omitted-field drift is thereby within "
        "the scope of the hash'.",
    ),
    (
        "key-order-ascii",
        "value",
        {"b": 1, "A": 2, "a": 3, "10": 4, "1": 5},
        "RFC 8785 sorts object member names by UTF-16 code unit, not by any locale collation: "
        "digits before uppercase before lowercase.",
    ),
    (
        "key-order-utf16-astral",
        "value",
        {
            "\ufffd\ufffd": "two-replacement-chars",
            "\U0001f600": "astral",
            "a": "ascii",
            "\ue000": "bmp-pua",
        },
        "The discriminator between UTF-16 code-unit ordering and code-point ordering: U+10000 "
        "and above begin with a high surrogate (0xD800..0xDBFF), so they sort BEFORE U+E000 and "
        "U+FFFD in UTF-16 order and AFTER them by code point. Python's native string comparison "
        "gets this wrong; the port sorts on big-endian UTF-16 bytes instead.",
    ),
    (
        "nfc-normalization",
        "value",
        {
            "e\u0301cole": "cafe\u0301",
            "stra\u00dfe": "gru\u0308n",
        },
        "PROFILE-DEFINED: v1 normalizes every key and every string value to NFC. Decomposed "
        "input hashes identically to precomposed input.",
    ),
    (
        "string-escapes",
        "value",
        {
            "named": "\b\t\n\f\r",
            "ctrl": "\u0000\u0001\u001f",
            "quote": "\"",
            "backslash": "\\",
            "solidus": "/",
            "del": "\u007f",
            "nbsp": "\u00a0",
        },
        "RFC 8785 3.2.2.2 escaping: named escapes for the five, backslash-u00xx lowercase hex "
        "below 0x20, and nothing else escaped - not the solidus, not DEL, not non-ASCII.",
    ),
    (
        "integers",
        "value",
        {
            "max": 9007199254740991,
            "min": -9007199254740991,
            "zero": 0,
            "negzero": -0.0,
            "int_valued_float": 100.0,
        },
        "PROFILE-DEFINED: v1 admits integers only. An integer-valued float is accepted and "
        "serialized as an integer; -0 normalizes to 0. Non-integer numbers are rejected.",
    ),
    (
        "array-order-preserved",
        "value",
        {"list": [3, 1, 2], "objs": [{"b": 1, "a": 2}, {"d": 4, "c": 3}]},
        "RFC 8785 leaves array order alone. Profile v1 reorders only 'line_items', and only in "
        "canonical_commitment(); every other array is order-significant.",
    ),
    (
        "unicode-values-literal",
        "value",
        {
            "cjk": "\u65e5\u672c\u8a9e",
            "emoji": "\U0001f642",
            "rtl": "\u0645\u0631\u062d\u0628\u0627",
        },
        "Non-ASCII output is literal UTF-8, never backslash-u escaped. The hash is over the "
        "UTF-8 bytes of that string.",
    ),
    (
        "commitment-canonical-order",
        "commitment",
        CART,
        "The 4.3 canonical authorization transaction commitment for the disclosure's worked "
        "example (1): a weekly grocery cart whose only divergence is a twenty-four-pack where "
        "the instruction said twelve. Line items already in profile order.",
    ),
    (
        "commitment-line-items-reversed",
        "commitment",
        REVERSED_CART,
        "PROFILE-DEFINED array ordering, demonstrated: the same cart with line_items in reverse "
        "producer order MUST yield the identical commitment. Compare the digest with "
        "'commitment-canonical-order'.",
    ),
    (
        "commitment-attempt-nonce-distinguishes",
        "commitment",
        RE_PRESENTED_CART,
        "v2.3 erratum (Section 4.3), the load-bearing case: this cart is byte-identical to "
        "'commitment-canonical-order' in every field except attempt_nonce - same seller, same "
        "line items, same totals, and the SAME checkout_id. Its digest MUST differ. A platform "
        "checkout or session identifier persists across cart mutations, so binding to checkout_id "
        "alone leaves two distinct presentations of the same cart indistinguishable, which is the "
        "re-presentation window this field closes. If this vector ever matches "
        "'commitment-canonical-order', the erratum has been silently reverted.",
    ),
    (
        "commitment-variant-null-sorts-first",
        "commitment",
        {
            "profile": DEFAULT_PROFILE_ID,
            "checkout_id": "chk-sort-demo",
            "created_at": "2026-08-27T00:00:00Z",
            "seller": {
                "seller_id": "seller:demo",
                "legal_name": "Demo",
                "merchant_category_code": None,
                "domain": None,
            },
            "currency": "USD",
            "currency_minor_unit_exponent": 2,
            "line_items": [
                {
                    "line_id": "b",
                    "sku": "SKU-X",
                    "variant_id": "24-pack",
                    "title": "X, 24-pack",
                    "quantity": 1,
                    "unit_amount_minor": 100,
                    "total_amount_minor": 100,
                    "fulfillment_source": {
                        "kind": "digital",
                        "location_id": None,
                        "marketplace_seller_id": None,
                    },
                },
                {
                    "line_id": "a",
                    "sku": "SKU-X",
                    "variant_id": None,
                    "title": "X",
                    "quantity": 1,
                    "unit_amount_minor": 100,
                    "total_amount_minor": 100,
                    "fulfillment_source": {
                        "kind": "digital",
                        "location_id": None,
                        "marketplace_seller_id": None,
                    },
                },
            ],
            "tax": {"total_amount_minor": 0, "inclusive": False, "components": []},
            "shipping": {
                "amount_minor": 0,
                "method": None,
                "destination": {
                    "country": None,
                    "region": None,
                    "postal_code": None,
                    "address_commitment": None,
                },
            },
            "totals": {
                "subtotal_minor": 200,
                "tax_minor": 0,
                "shipping_minor": 0,
                "discount_minor": 0,
                "grand_total_minor": 200,
            },
            "fulfillment_source": {
                "kind": "digital",
                "location_id": None,
                "marketplace_seller_id": None,
            },
            "recurrence": None,
            "substitution_policy": {
                "mode": "none",
                "allowed_substitutions": [],
                "max_unit_amount_delta_minor": None,
                "notify_principal": False,
            },
        },
        "Line-item sort key is (sku, variant_id, line_id); an explicit null variant_id sorts as "
        "the empty string, i.e. before any non-empty variant.",
    ),
]

REJECT = [
    (
        "reject-non-integer-number",
        "value",
        {"amount": 1.5},
        "E_NON_INTEGER_NUMBER",
        "PROFILE-DEFINED: money is integer minor units. A decimal amount is a profile violation, "
        "not a rounding question.",
    ),
    (
        "reject-integer-out-of-range",
        "value",
        {"n": 9007199254740992},
        "E_INTEGER_OUT_OF_RANGE",
        "Outside the exactly-representable IEEE-754 integer range, so the two ports could "
        "disagree. Rejected rather than approximated.",
    ),
    (
        "reject-lone-surrogate",
        "value",
        {"s": "\ud800"},
        "E_LONE_SURROGATE",
        "An unpaired surrogate has no UTF-8 encoding. Rejected rather than replaced with U+FFFD, "
        "which would silently change the committed text.",
    ),
    (
        "reject-duplicate-key-after-nfc",
        "value",
        {"\u00e9": 1, "e\u0301": 2},
        "E_DUPLICATE_KEY_AFTER_NFC",
        "Two distinct JSON keys that collide once normalized to NFC. Merging them would let two "
        "different documents hash to one commitment, so the profile refuses the document.",
    ),
]

vectors = []
for name, mode, value, note in ACCEPT:
    if mode == "commitment":
        out = canonical_commitment(value)
        vectors.append(
            {
                "name": name,
                "mode": mode,
                "note": note,
                "input": value,
                "expected_jcs": out["canonical"],
                "expected_digest": out["digest"],
            }
        )
    else:
        vectors.append(
            {
                "name": name,
                "mode": mode,
                "note": note,
                "input": value,
                "expected_jcs": canonicalize(value),
                "expected_digest": digest(value),
            }
        )

rejects = []
for name, mode, value, code, note in REJECT:
    try:
        canonical_commitment(value) if mode == "commitment" else canonicalize(value)
    except CanonicalizationError as exc:
        assert exc.code == code, f"{name}: expected {code}, got {exc.code}"
    else:
        raise AssertionError(f"{name}: expected {code}, no error raised")
    rejects.append(
        {
            "name": name,
            "mode": mode,
            "note": note,
            "input": value,
            "expected_error_code": code,
        }
    )

doc = {
    "$comment": (
        "Shared canonicalization test vectors for mandatepatch/profile/v1. Regenerate with "
        "scripts/build-vectors.py. The TypeScript and Python ports MUST both reproduce every "
        "expected_jcs and expected_digest byte for byte, and MUST both raise the named error "
        "code for every reject vector."
    ),
    "profile": DEFAULT_PROFILE_ID,
    "serialization": "RFC 8785 JSON Canonicalization Scheme (JCS)",
    "hash": (
        "SHA-256 over the UTF-8 bytes of the canonical string, base64url without padding, "
        "prefixed 'sha-256:'"
    ),
    "vectors": vectors,
    "rejects": rejects,
}

out_path = os.path.join(ROOT, "examples", "canonicalization-vectors.json")
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, ensure_ascii=True, indent=2, sort_keys=False)
    fh.write("\n")
print(f"wrote {out_path}: {len(vectors)} accept vectors, {len(rejects)} reject vectors")
