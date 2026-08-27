#!/usr/bin/env python3
"""Regenerate examples/*.example.json.

The five example instances cross-reference each other by hash: the divergence
record binds the commitment, the patch binds the divergence record and the mandate
version, the supersession record binds the predecessor mandate. Writing them by
hand would guarantee stale hashes, so they are generated with the profile's own
digest function and checked into the repository.

Signature values in these examples are PLACEHOLDERS. This repository ships no
signing or verification code; the bytes in `human_signature.signature` and
`encrypted_score.ciphertext` are illustrative padding, not real cryptographic
output, and nothing here should be read as a verified artifact.

The scenario is the disclosure's own worked example (section 1): a standing weekly
grocery mandate that names a twelve-pack; one week only a twenty-four-pack is in
stock; the cart passes every machine-enforceable constraint and diverges only in
meaning.
"""
import base64
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

from mandatepatch.canonicalize import (  # noqa: E402
    DEFAULT_PROFILE_ID,
    canonical_commitment,
    digest,
)

EX = os.path.join(ROOT, "examples")


def h(label):
    """A real, reproducible SHA-256 standing in for a measurement this repo cannot produce."""
    return digest({"example_placeholder": label})


#: The mandate's binding profile, one of the ds_tag inputs.
BINDING_PROFILE = "ap2/v0.2"


def _lp(x):
    """LP(x) = uint16 big-endian byte length of utf-8 x, followed by those bytes."""
    b = str(x).encode("utf-8")
    return struct.pack(">H", len(b)) + b


def _b64u(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def ds_tag(sep, binding_profile=BINDING_PROFILE):
    """6.2 domain-separation tag, computed for real from the components beside it.

    PROFILE-DEFINED, DECIDED: profile v1 carries this tag in the JSON body AND
    requires it to byte-equal the separator bound into the carrier's signed input
    (WebAuthn clientDataJSON.challenge, or KB-JWT aud/nonce). Length-prefixed with
    NO delimiters, because relying_party and mandate_family_id are attacker-
    influenced. The 'transcript' prefix must differ from 7's 'nullifier' prefix so a
    transcript tag and a nullifier tag can never collide.
    """
    buf = b"MandateLifecycle/v1/transcript"
    for value in (
        sep["purpose"],
        sep["audience"],
        sep["relying_party"],
        sep["mandate_family_id"],
        sep["mandate_version"],
        sep["rail"],
        binding_profile,
    ):
        buf += _lp(value)
    return _b64u(hashlib.sha256(buf).digest())


def kid(label):
    """Reproducible stand-in for base64url(SHA-256(SPKI DER)), profile v1's key id.

    This repository ships no key material, so the SPKI bytes are a labelled
    placeholder. The DERIVATION SHAPE, the encoding, and the 43-character unpadded
    base64url length are exactly what profile v1 requires.
    """
    return _b64u(hashlib.sha256(("spki-der-placeholder:" + label).encode("utf-8")).digest())


def anchor(label, epoch):
    """A 5.2-transparency-log time anchor, stapled at signing time.

    Optional but recommended: without it, signed_at is self-asserted, which is
    adequate for routine verification and not for dispute-grade evidence. Carried on
    the two artifacts 4.4 names as 'the dispute-evidence bundle' - the patch and its
    divergence record - and deliberately omitted from the mandate and the
    supersession record, so the example set exercises both present and absent.
    """
    return {
        "log_id": "log:northside-wallet-transparency",
        "epoch": epoch,
        "inclusion_proof": [
            _b64u(hashlib.sha256(f"audit-path:{label}:{i}".encode("utf-8")).digest())
            for i in range(3)
        ],
    }



def write(name, obj):
    path = os.path.join(EX, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"  wrote {name}")
    return obj


DOMAIN_SEP = {
    "audience": "acquirer:northside-psp",
    "relying_party": "seller:northside-market",
    "mandate_family_id": "fam:weekly-groceries-8f21",
    "mandate_version": 1,
    "rail": "card:visa",
    "purpose": "mandatepatch/delta-authorization+resumption",
}

MANDATE_SEP = dict(DOMAIN_SEP, purpose="mandatepatch/mandate-creation")
DIVERGENCE_SEP = dict(DOMAIN_SEP, purpose="mandatepatch/divergence-record")
SUPERSESSION_SEP = dict(DOMAIN_SEP, purpose="mandatepatch/supersession")

#: 1: the principal's passkey. 3: only the innermost principal signature is
#: accept-bearing; service keys are reject-only and rotate freely.
PRINCIPAL_KID = kid("principal/passkey-7a1c")
WALLET_SCORER_KID = kid("wallet/divergence-scorer-2026Q3")

AUTHENTICATOR = {
    "credential_id": "cred:passkey-7a1c",
    "kind": "platform-authenticator",
    "device_bound": True,
    "channel_independent": True,
}

# ---------------------------------------------------------------- 4.3 ----

commitment = {
    "profile": DEFAULT_PROFILE_ID,
    "checkout_id": "chk:2026-W35-northside-0417",
    "attempt_nonce": "Zk9tQ1hyVGJ3TDJfNmhOcEE",
    "created_at": "2026-08-27T14:02:11Z",
    "seller": {
        "seller_id": "seller:northside-market",
        "legal_name": "Northside Market LLC",
        "merchant_category_code": "5411",
        "domain": "northsidemarket.example",
    },
    "currency": "USD",
    "currency_minor_unit_exponent": 2,
    "line_items": [
        {
            "line_id": "li-001",
            "sku": "SKU-BREAD-SOURDOUGH",
            "variant_id": None,
            "title": "Sourdough loaf, 700 g",
            "quantity": 2,
            "unit_amount_minor": 549,
            "total_amount_minor": 1098,
            "fulfillment_source": {
                "kind": "ship-from-store",
                "location_id": "store:northside-04",
                "marketplace_seller_id": None,
            },
        },
        {
            "line_id": "li-002",
            "sku": "SKU-COLA-CANS",
            "variant_id": "24-pack",
            "title": "Fizzwater Cola, 24-pack cans",
            "quantity": 1,
            "unit_amount_minor": 1349,
            "total_amount_minor": 1349,
            "fulfillment_source": {
                "kind": "ship-from-store",
                "location_id": "store:northside-04",
                "marketplace_seller_id": None,
            },
        },
        {
            "line_id": "li-003",
            "sku": "SKU-MILK-WHOLE",
            "variant_id": "1-gallon",
            "title": "Whole milk, 1 gallon",
            "quantity": 1,
            "unit_amount_minor": 429,
            "total_amount_minor": 429,
            "fulfillment_source": {
                "kind": "ship-from-store",
                "location_id": "store:northside-04",
                "marketplace_seller_id": None,
            },
        },
    ],
    "tax": {
        "total_amount_minor": 209,
        "inclusive": False,
        "components": [
            {
                "kind": "sales",
                "jurisdiction": "US-NY",
                "rate_basis_points": 725,
                "amount_minor": 209,
            }
        ],
    },
    "shipping": {
        "amount_minor": 499,
        "method": "same-day-delivery",
        "destination": {
            "country": "US",
            "region": "NY",
            "postal_code": "10025",
            "address_commitment": h("destination-address"),
        },
    },
    "totals": {
        "subtotal_minor": 2876,
        "tax_minor": 209,
        "shipping_minor": 499,
        "discount_minor": 0,
        "grand_total_minor": 3584,
    },
    "fulfillment_source": {
        "kind": "ship-from-store",
        "location_id": "store:northside-04",
        "marketplace_seller_id": None,
    },
    "recurrence": None,
    "substitution_policy": {
        "mode": "equivalent-only",
        "allowed_substitutions": [],
        "max_unit_amount_delta_minor": 100,
        "notify_principal": True,
    },
}

print("building examples...")
write("canonical-commitment.example.json", commitment)
checkout_commitment = canonical_commitment(commitment)["digest"]

# ------------------------------------------------------------ mandate ----

SCORING_STACK = {
    "stack_measurement": h("scoring-stack/v3"),
    "stack_version": 3,
    "model_hash": h("embedding-model"),
    "tokenizer_hash": h("tokenizer"),
    "normalization_rules_hash": h("normalization-rules"),
    "preprocessing_hash": h("preprocessing"),
    "quantization": "int8",
    "runtime_configuration_hash": h("runtime-configuration"),
}

mandate = {
    "schema_version": "mandatepatch/mandate/v1",
    "canonicalization_profile": DEFAULT_PROFILE_ID,
    "binding_profile": "ap2/v0.2",
    "mandate_family_id": "fam:weekly-groceries-8f21",
    "mandate_version": 1,
    "supersedes": None,
    "epoch": 1,
    "instruction": {
        "source_text": (
            "Every week, buy my usual groceries from the usual store - the usual staples, "
            "including a twelve-pack of Fizzwater Cola - and keep it under $150."
        ),
        "source_bytes_hash": h("instruction-source-bytes"),
        "machine_interpretation": {
            "cadence": "weekly",
            "merchant_allowlist": ["seller:northside-market"],
            "amount_cap_minor": 15000,
            "named_items": [{"sku_family": "SKU-COLA-CANS", "variant_id": "12-pack"}],
        },
        "machine_interpretation_hash": h("machine-interpretation"),
        "surfaced_conflicts": [],
    },
    "semantic_gate": {
        "baseline_commitment": h("commit(E0)||salt"),
        "commitment_scheme": "sha-256(E0||salt)",
        "salt_disclosure_policy": "dispute-only",
        "scoring_stack": SCORING_STACK,
        "threshold_micro": 180000,
        "category_taxonomy": {
            "taxonomy_id": "taxonomy:retail-grocery",
            "taxonomy_version": 2,
            "categories": [
                {"category_id": "grocery.staples", "threshold_micro": 220000},
                {"category_id": "grocery.beverage.packaged", "threshold_micro": 180000},
            ],
        },
        "threshold_selection_rule": "most-conservative-matching-category",
        "aggregation": "per-line-item-worst-case",
        "deployment_variant": {"kind": "wallet-side", "enclave_measurement": None},
        "cumulative_divergence_budget_micro": 1500000,
        "attempt_budget": 3,
        "cart_revision_throttle": 2,
        "agent_visible_outcome_space": ["pass", "suspend"],
        "score_disclosure": "encrypted-to-principal-and-issuer",
    },
    "predicates": [
        {
            "predicate_id": "pred-amount-cap",
            "kind": "machine-enforceable",
            "owner": "principal",
            "patchable": True,
            "expression": {"op": "lte", "field": "totals.grand_total_minor", "value": 15000},
            "description": "Total authorized amount must not exceed USD 150.00.",
        },
        {
            "predicate_id": "pred-merchant-allowlist",
            "kind": "machine-enforceable",
            "owner": "principal",
            "patchable": True,
            "expression": {
                "op": "in",
                "field": "seller.seller_id",
                "value": ["seller:northside-market"],
            },
            "description": "Seller must be the usual store.",
        },
        {
            "predicate_id": "pred-semantic-cart",
            "kind": "semantic",
            "owner": "principal",
            "patchable": True,
            "expression": {
                "op": "semantic-divergence-within-threshold",
                "baseline": "semantic_gate.baseline_commitment",
                "aggregation": "per-line-item-worst-case",
            },
            "description": (
                "Each line item must remain within the mandate's semantic distance threshold of "
                "the committed instruction baseline."
            ),
        },
        {
            "predicate_id": "pred-cumulative-scope-budget",
            "kind": "cumulative-budget",
            "owner": "principal",
            "patchable": True,
            "expression": {"op": "within-multidimensional-budget", "axes": [
                "semantic_distance_micro", "monetary_delta_minor", "merchant_set_delta"]},
            "description": "Accumulated patch scope must remain within the per-axis budget.",
        },
        {
            "predicate_id": "pred-issuer-category-restriction",
            "kind": "machine-enforceable",
            "owner": "issuer",
            "patchable": False,
            "expression": {"op": "not-in", "field": "seller.merchant_category_code",
                           "value": ["7995"]},
            "description": (
                "Issuer-pinned category restriction. Unpatchable by the principal: a MandatePatch "
                "cannot make a transaction permissible that a third party's independent policy "
                "prohibits."
            ),
        },
        {
            "predicate_id": "pred-freshness",
            "kind": "freshness",
            "owner": "issuer",
            "patchable": False,
            "expression": {"op": "head-at-epoch-within", "delta_seconds": 30},
            "description": (
                "Mandate version must have been family head at an epoch not older than the "
                "staleness bound, checked at authorization and re-checked at capture."
            ),
        },
    ],
    "patch_chain_governance": {
        "patch_of_patch_permitted": False,
        "max_patches_before_forced_supersession": 3,
        "cooling_off_seconds": 3600,
        "full_context_redisplay_required": True,
        "base_locked_while_patch_pending": True,
        "cumulative_scope_budget": {
            "semantic_distance_micro": 750000,
            "monetary_delta_minor": 5000,
            "merchant_set_delta": 0,
        },
        "settled_patch_derived_spend_counts": True,
    },
    "freshness": {
        "staleness_bound_seconds": 30,
        "revocation_mode": "bounded-staleness",
        "head_source": "transparency-log",
        "cosigned_heads_required": True,
        "evaluation_points": ["authorization", "capture"],
    },
    "consume_authority": {
        "authority_id": "registry:wallet.example/fam/weekly-groceries-8f21",
        "kind": "wallet",
        "linearizable": True,
    },
    "challenge_policy": {
        "challenge_ttl_seconds": 900,
        "expiry_disposition": "void-checkout",
        "max_outstanding_challenges": 2,
        "max_candidates_per_challenge": 3,
        "assurance_profile": "aal2-device-bound-independent-channel",
        "device_bound_credential_required": True,
        "channel_independence_required": True,
        "decline_all_is_first_class": True,
    },
    "presentation_policy": {
        "renderer_profile": "draft-schrock-ep-presentation-binding-00",
        "deterministic_rendering_required": True,
        "neutralization_required": True,
        "render_state_hash_required": True,
        "minimum_attestation_tier": "os-composited",
        "font_hash": h("pinned-font"),
        "locale": "en-US",
        "render_to_input_event_binding_required": True,
    },
    "issued_at": "2026-06-01T09:00:00Z",
    "expiry": None,
    "render_state_hash": h("mandate-render-state"),
    "attestation_tier": "os-composited",
    "human_signature": {
        "kid": PRINCIPAL_KID,
        "alg": "ES256",
        "signed_at": "2026-06-01T09:00:00Z",
        "authenticator": AUTHENTICATOR,
        "assurance_profile": "aal2-device-bound-independent-channel",
        "domain_separation": MANDATE_SEP,
        "ds_tag": ds_tag(MANDATE_SEP),
        "signature": "PLACEHOLDER-not-a-real-signature-mandate-v1",
    },
}
write("mandate.example.json", mandate)
base_mandate_hash = digest(mandate)

# ------------------------------------------------------------------ 3 ----

divergence = {
    "schema_version": "mandatepatch/divergence-record/v1",
    "record_id": "dr:2026-W35-northside-0417-1",
    "mandate_family_id": "fam:weekly-groceries-8f21",
    "mandate_version": 1,
    "base_mandate_hash": base_mandate_hash,
    "checkout_commitment": checkout_commitment,
    "evaluated_at": "2026-08-27T14:02:13Z",
    "deployment_variant": {"kind": "wallet-side", "enclave_attestation": None},
    "scoring_stack": {"stack_measurement": SCORING_STACK["stack_measurement"], "stack_version": 3},
    "threshold_applied_micro": 180000,
    "category_id_applied": "grocery.beverage.packaged",
    "aggregation": "per-line-item-worst-case",
    "cart_level_score_commitment": h("cart-level-score"),
    "line_item_scores": [
        {"line_id": "li-001", "score_commitment": h("score/li-001"), "exceeded_threshold": False},
        {"line_id": "li-002", "score_commitment": h("score/li-002"), "exceeded_threshold": True},
        {"line_id": "li-003", "score_commitment": h("score/li-003"), "exceeded_threshold": False},
    ],
    "score_commitment": h("worst-case-aggregate-score"),
    "encrypted_score": {
        "ciphertext": "PLACEHOLDER-ciphertext-encrypted-to-principal-and-issuer",
        "recipients": ["principal", "issuer"],
        "encryption_alg": "ECDH-ES+A256GCM",
    },
    "outcome": "suspend",
    "reason_codes": ["SEMANTIC_DIVERGENCE"],
    "flagged_line_ids": ["li-002"],
    "failing_predicate_ids": ["pred-semantic-cart"],
    "cumulative_divergence_after_micro": 310000,
    "attempt_index": 1,
    "previous_record_hash": None,
    "signature": {
        "kid": WALLET_SCORER_KID,
        "alg": "ES256",
        "signed_at": "2026-08-27T14:02:13Z",
        "signer": "wallet.example",
        "signer_role": "wallet",
        "domain_separation": DIVERGENCE_SEP,
        "ds_tag": ds_tag(DIVERGENCE_SEP),
        "anchor": anchor("divergence-record", 1),
        "signature": "PLACEHOLDER-not-a-real-signature-divergence-record",
    },
}
write("divergence-record.example.json", divergence)
divergence_record_ref = digest(divergence)

# ------------------------------------------------------------------ 4 ----

patch = {
    "base_mandate_hash": base_mandate_hash,
    "patch_sequence": 1,
    "violations": [
        {
            "violated_predicate_id": "pred-semantic-cart",
            "value_old": {"approved_line_ids": []},
            "value_new": {"approved_line_ids": ["li-002"]},
        }
    ],
    "checkout_commitment": checkout_commitment,
    "suspended_state_hash": h("suspended-agent-execution-state"),
    "divergence_record_ref": divergence_record_ref,
    "nonce": "n-4f2b9c1e7a6d0835",
    "issued_at": "2026-08-27T14:06:40Z",
    "expiry": "2026-08-27T14:21:40Z",
    "render_state_hash": h("patch-render-state"),
    "attestation_tier": "os-composited",
    "human_signature": {
        "kid": PRINCIPAL_KID,
        "alg": "ES256",
        "signed_at": "2026-08-27T14:06:40Z",
        "authenticator": AUTHENTICATOR,
        "assurance_profile": "aal2-device-bound-independent-channel",
        "domain_separation": DOMAIN_SEP,
        "ds_tag": ds_tag(DOMAIN_SEP),
        "anchor": anchor("mandate-patch-seq1", 1),
        "signature": "PLACEHOLDER-not-a-real-signature-mandatepatch-seq1",
    },
}
write("mandate-patch.example.json", patch)

# ------------------------------------------------------------------ 5 ----

supersession = {
    "schema_version": "mandatepatch/supersession-record/v1",
    "record_id": "sr:fam-weekly-groceries-8f21-epoch2",
    "mandate_family_id": "fam:weekly-groceries-8f21",
    "action": "supersede",
    "supersedes": base_mandate_hash,
    "predecessor_version": 1,
    "successor_mandate_hash": h("mandate-v2"),
    "successor_version": 2,
    "epoch": 2,
    "family_head": h("family-head-epoch-2"),
    "head_source": {
        "kind": "transparency-log",
        "cosigned_heads": True,
        "witnesses": ["witness:alpha.example", "witness:beta.example"],
        "operator_id": None,
        "trust_model": "cosigned-log-with-witnesses",
    },
    "staleness_bound_seconds": 30,
    "revocation_mode": "bounded-staleness",
    "re_baseline": {
        "new_baseline_commitment": h("commit(E0-v2)||salt"),
        "commitment_scheme": "sha-256(E0||salt)",
        "scoring_stack_measurement": SCORING_STACK["stack_measurement"],
        "scoring_stack_version": 3,
        "instruction_source_bytes_hash": h("instruction-source-bytes-v2"),
    },
    "in_flight_resolution": {
        "authorized_before": "honor",
        "in_flight_at": "re-evaluate-at-capture",
        "initiated_after": "evaluate-against-successor",
        "evaluation_points": ["authorization", "capture"],
    },
    "voided_patch_nullifiers": ["nf-8c11a0d7e35f4b62"],
    "nullifier_epoch_update_ordering": "nullify-then-advance",
    "atomicity_window_ms": 40,
    "consume_authority": {
        "authority_id": "registry:wallet.example/fam/weekly-groceries-8f21",
        "kind": "wallet",
        "linearizable": True,
    },
    "effective_at": "2026-09-03T08:15:00Z",
    "forced_by_patch_exhaustion": False,
    "full_context_redisplay": True,
    "cooling_off_observed_seconds": 3600,
    "render_state_hash": h("supersession-render-state"),
    "attestation_tier": "os-composited",
    "human_signature": {
        "kid": PRINCIPAL_KID,
        "alg": "ES256",
        "signed_at": "2026-09-03T08:15:00Z",
        "authenticator": AUTHENTICATOR,
        "assurance_profile": "aal2-device-bound-independent-channel",
        "domain_separation": SUPERSESSION_SEP,
        "ds_tag": ds_tag(SUPERSESSION_SEP),
        "signature": "PLACEHOLDER-not-a-real-signature-supersession-epoch2",
    },
}
write("supersession-record.example.json", supersession)

print(f"  checkout_commitment  = {checkout_commitment}")
print(f"  base_mandate_hash    = {base_mandate_hash}")
print(f"  divergence_record_ref= {divergence_record_ref}")
print(f"  principal kid        = {PRINCIPAL_KID}")
print(f"  wallet scorer kid    = {WALLET_SCORER_KID}")
print(f"  ds_tag (patch)       = {ds_tag(DOMAIN_SEP)}")
