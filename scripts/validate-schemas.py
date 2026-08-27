#!/usr/bin/env python3
"""Schema conformance checks.

Positive: every examples/*.example.json validates against its schema.
Negative: a set of deliberate mutations MUST be rejected. The negative cases exist
because several rules from the disclosure are encoded as schema constraints rather
than prose, and a schema edit that quietly drops one of them would otherwise pass CI.
"""
from __future__ import annotations

import copy
import json
import os
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAIRS = [
    ("canonical-commitment.schema.json", "canonical-commitment.example.json"),
    ("mandate.schema.json", "mandate.example.json"),
    ("mandate-patch.schema.json", "mandate-patch.example.json"),
    ("divergence-record.schema.json", "divergence-record.example.json"),
    ("supersession-record.schema.json", "supersession-record.example.json"),
]


def load(kind, name):
    with open(os.path.join(ROOT, kind, name), encoding="utf-8") as fh:
        return json.load(fh)


def validator(schema_name):
    return Draft202012Validator(load("schemas", schema_name), format_checker=FormatChecker())


def mutations():
    """(label, schema, instance, why) - each MUST fail validation."""
    patch = load("examples", "mandate-patch.example.json")
    mandate = load("examples", "mandate.example.json")
    supersession = load("examples", "supersession-record.example.json")
    commitment = load("examples", "canonical-commitment.example.json")
    divergence = load("examples", "divergence-record.example.json")

    m1 = copy.deepcopy(patch)
    del m1["nonce"]

    m2 = copy.deepcopy(patch)
    m2["base_patch_hash"] = m2["base_mandate_hash"]

    m3 = copy.deepcopy(patch)
    m3["violations"] = []

    m4 = copy.deepcopy(mandate)
    for p in m4["predicates"]:
        if p["predicate_id"] == "pred-issuer-category-restriction":
            p["patchable"] = True

    m5 = copy.deepcopy(mandate)
    m5["patch_chain_governance"]["patch_of_patch_permitted"] = True

    m6 = copy.deepcopy(supersession)
    m6["re_baseline"] = None

    m7 = copy.deepcopy(supersession)
    m7["action"] = "revoke"

    m8 = copy.deepcopy(commitment)
    del m8["recurrence"]

    m9 = copy.deepcopy(commitment)
    m9["line_items"][0]["unit_amount_minor"] = 5.49

    m16 = copy.deepcopy(commitment)
    del m16["attempt_nonce"]

    m10 = copy.deepcopy(patch)
    m10["attestation_tier"] = "screenshot"

    # --- key-identifier envelope (B3 adjudication) ---------------------------
    # These five exist because the envelope fields are NOT retrofittable: evidence
    # signed without them is verifiable only by trial-verification against every
    # historical key, which goes ambiguous the instant two keys coexist. A schema
    # edit that quietly made any of them optional would otherwise pass CI.

    m11 = copy.deepcopy(patch)
    del m11["human_signature"]["kid"]

    m12 = copy.deepcopy(patch)
    del m12["human_signature"]["signed_at"]

    m13 = copy.deepcopy(patch)
    del m13["human_signature"]["anchor"]["epoch"]

    m14 = copy.deepcopy(divergence)
    m14["signature"]["alg"] = "HS256"

    m15 = copy.deepcopy(supersession)
    del m15["human_signature"]["ds_tag"]

    return [
        ("patch-missing-nonce", "mandate-patch.schema.json", m1,
         "4.2 lists nonce among the fields entering the signed transcript"),
        ("patch-of-patch-field", "mandate-patch.schema.json", m2,
         "4.2: 'Patch-of-patch is prohibited' - additionalProperties false blocks inventing one"),
        ("patch-empty-violations", "mandate-patch.schema.json", m3,
         "4.2: 'one or more (violated_predicate_id, value_old, value_new) tuples'"),
        ("issuer-predicate-marked-patchable", "mandate.schema.json", m4,
         "4.2: an issuer-pinned predicate 'is unpatchable by the principal'"),
        ("patch-of-patch-permitted-true", "mandate.schema.json", m5,
         "4.2: 'Patch-of-patch is prohibited'"),
        ("supersede-without-re-baseline", "supersession-record.schema.json", m6,
         "5.1: 'amendment carries semantic re-baselining - a new committed E0'"),
        ("revoke-carrying-successor", "supersession-record.schema.json", m7,
         "5.1: a revocation has no successor mandate and no re-baseline"),
        ("commitment-omitted-field", "canonical-commitment.schema.json", m8,
         "4.3: 'Omitted-field drift is thereby within the scope of the hash' - explicit null, never omission"),
        ("commitment-decimal-money", "canonical-commitment.schema.json", m9,
         "PROFILE-DEFINED: money is integer minor units, never a float"),
        ("patch-unknown-attestation-tier", "mandate-patch.schema.json", m10,
         "6.3: the tier vocabulary is hardware / OS-composited / software"),
        ("signature-missing-kid", "mandate-patch.schema.json", m11,
         "B3: without a key identifier, evidence is verifiable only by trial-verification "
         "against every historical key - ambiguous the instant two keys coexist"),
        ("signature-missing-signed-at", "mandate-patch.schema.json", m12,
         "B3: signed_at is the instant key-validity intervals are evaluated against - "
         "verify against the key current at signing time, never the key current now"),
        ("signature-malformed-anchor", "mandate-patch.schema.json", m13,
         "B3: an anchor without its epoch cannot locate a cosigned head, so it proves "
         "nothing about when the signature existed"),
        ("signature-unknown-alg", "divergence-record.schema.json", m14,
         "PROFILE-DEFINED: profile v1's suite is ES256/384/512, EdDSA, RS256, PS256 - "
         "a symmetric MAC is not a signature and must not validate"),
        ("signature-missing-ds-tag", "supersession-record.schema.json", m15,
         "6.2: an envelope with separator components but no tag is exactly the "
         "ambiguity the transplant attack needs in order to succeed"),
        ("commitment-missing-attempt-nonce", "canonical-commitment.schema.json", m16,
         "4.3 v2.3 erratum: without the per-attempt distinguisher, two presentations of an "
         "unchanged cart under one checkout_id commit to the same bytes - the re-presentation "
         "window. The field is required, not optional"),
    ]


def main() -> int:
    failures = []

    print("positive cases")
    for schema_name, example_name in PAIRS:
        v = validator(schema_name)
        errors = sorted(v.iter_errors(load("examples", example_name)), key=lambda e: e.path)
        if errors:
            failures.append(f"{example_name} SHOULD validate against {schema_name}")
            for e in errors[:5]:
                failures.append(f"    {list(e.path)}: {e.message}")
        else:
            print(f"  ok    {example_name} validates against {schema_name}")

    print("negative cases (each MUST be rejected)")
    for label, schema_name, instance, why in mutations():
        v = validator(schema_name)
        if v.is_valid(instance):
            failures.append(f"{label} SHOULD have been rejected by {schema_name} -- {why}")
        else:
            print(f"  ok    {label} rejected  [{why}]")

    if failures:
        print("\nFAIL", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        return 1
    print(f"\nPASS  {len(PAIRS)} examples valid, {len(mutations())} mutations rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
