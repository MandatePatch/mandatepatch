"""TypedDict stubs mirroring ``schemas/*.schema.json``.

These are shapes only. This repository ships the artifact layer: it defines the
objects and their canonical form, and implements no scorer, no service, and no
policy engine. Nothing here evaluates a predicate, computes an embedding, consumes
a nullifier, or renders a challenge.

Section references are to Technical Disclosure Commons #11517, "Mandate Lifecycle
Extensions for Agentic Payment Credentials" (Matt Kirby, CC-BY).
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

#: ``sha-256:<base64url-unpadded>`` under ``mandatepatch/profile/v1``. PROFILE-DEFINED encoding.
Hash = str

#: RFC 3339 date-time.
Timestamp = str

#: 6.3: "hardware secure-display, OS-composited, software", the last "declared evidentially weak".
AttestationTier = Literal["hardware", "os-composited", "software"]


class DomainSeparation(TypedDict):
    """6.2: 'domain-separated over audience, relying party, mandate family and version, rail, and protocol purpose'."""

    audience: str
    relying_party: str
    mandate_family_id: str
    mandate_version: int
    rail: str
    purpose: str


class Authenticator(TypedDict):
    """6.2: assurance profiles are 'named tiers of authenticator strength and channel independence'."""

    credential_id: str
    kind: str
    device_bound: bool
    channel_independent: bool


#: PROFILE-DEFINED: profile v1's algorithm suite. ES256/ES384/ES512 is the ECDSA set
#: AP2 v0.2 requires of its bindings; EdDSA is Ed25519; RS256/PS256 appear on deployed
#: WebAuthn authenticators. A binding profile MAY narrow this union; widening it takes
#: a new profile identifier.
SignatureAlg = Literal["ES256", "ES384", "ES512", "EdDSA", "RS256", "PS256"]


class Anchor(TypedDict):
    """Independent evidence that a signature existed at its ``signed_at``.

    PROFILE-DEFINED: profile v1 anchors into the 5.2 transparency log rather than
    standing up a second one - 5.2 already requires 'cosigned heads or a witness
    network against split-view equivocation', which is exactly what a time anchor
    needs. The recorded alternative is an RFC 3161 timestamp authority, which a 5.2
    issuer-registry deployment needs instead because it may run no log at all.

    Optional but RECOMMENDED: omit it and ``signed_at`` is self-asserted, which is
    fine for routine verification and not adequate for dispute-grade evidence.
    """

    log_id: str
    epoch: int
    #: Merkle audit path, leaf-ward to root-ward, base64url unpadded.
    inclusion_proof: list[str]


class KeyBinding(TypedDict):
    """Envelope fields every signed artifact carries so its signature survives rotation.

    A signature verifies iff ``signed_at`` falls inside the [not_before, not_after]
    interval recorded for ``kid`` - that is, against THE KEY CURRENT AT SIGNING TIME,
    never the key current now. Rejecting evidence because its key was later rotated
    is a bug, not a security property.

    These are not retrofittable. Evidence signed without them is verifiable only by
    trial-verification against every historical key, which goes ambiguous the instant
    two keys coexist - which is why they are present from the first commit.
    """

    #: ``base64url(SHA-256(SPKI DER))``, unpadded. Content-derived: a directory
    #: resolves a kid, it never defines one.
    kid: str
    alg: SignatureAlg
    #: RFC 3339, 'Z', second precision - the same form as every other timestamp here.
    signed_at: Timestamp
    #: 6.2 domain-separator digest. PROFILE-DEFINED, DECIDED: profile v1 carries the
    #: tag in the JSON body AND requires it to byte-equal the separator bound into the
    #: carrier's signed input (WebAuthn ``clientDataJSON.challenge``, or KB-JWT
    #: ``aud``/``nonce``). The body copy makes evidence checkable offline; the carrier
    #: copy is what makes the separator signature-covered. Recorded alternative:
    #: carrier-only, rejected for v1.
    ds_tag: str
    anchor: NotRequired[Anchor]


class HumanSignature(KeyBinding):
    """4.2: 'authenticator-bound; domain-separated per Section 6'."""

    authenticator: Authenticator
    assurance_profile: str
    domain_separation: DomainSeparation
    signature: str


# ------------------------------------------------------------------- 4.3 ----


class FulfillmentSource(TypedDict):
    kind: Literal["ship-from-warehouse", "ship-from-store", "pickup", "marketplace-seller", "digital"]
    location_id: str | None
    marketplace_seller_id: str | None


class LineItem(TypedDict):
    line_id: str
    sku: str
    variant_id: str | None
    title: str
    quantity: int
    unit_amount_minor: int
    total_amount_minor: int
    fulfillment_source: FulfillmentSource


class TaxComponent(TypedDict):
    kind: str
    jurisdiction: str
    rate_basis_points: int
    amount_minor: int


class Tax(TypedDict):
    total_amount_minor: int
    inclusive: bool
    components: list[TaxComponent]


class Destination(TypedDict):
    country: str | None
    region: str | None
    postal_code: str | None
    address_commitment: Hash | None


class Shipping(TypedDict):
    amount_minor: int
    method: str | None
    destination: Destination


class Totals(TypedDict):
    subtotal_minor: int
    tax_minor: int
    shipping_minor: int
    discount_minor: int
    grand_total_minor: int


class Recurrence(TypedDict):
    interval: Literal["day", "week", "month", "year"]
    interval_count: int
    occurrences: int | None
    until: Timestamp | None
    first_charge_at: Timestamp
    amount_variability: Literal["fixed", "variable"]
    max_amount_minor: int | None


class AllowedSubstitution(TypedDict):
    line_id: str
    sku: str
    variant_id: str | None


class SubstitutionPolicy(TypedDict):
    mode: Literal["none", "equivalent-only", "enumerated", "merchant-discretion"]
    allowed_substitutions: list[AllowedSubstitution]
    max_unit_amount_delta_minor: int | None
    notify_principal: bool


class Seller(TypedDict):
    seller_id: str
    legal_name: str
    merchant_category_code: str | None
    domain: str | None


class CanonicalCommitment(TypedDict):
    """4.3: 'seller identity, line items with SKU and variant identifiers, quantities,
    unit and total amounts, currency, tax, shipping, fulfillment source, recurrence
    terms, and post-authorization substitution policy.' Also 'the sole input to
    Section 3 scoring and the sole permissible display source for Section 6 challenges.'
    """

    profile: str
      checkout_id: str
    #: §4.3 (v2.3 erratum): 16-byte attempt distinguisher; required.
    attempt_nonce: str
    created_at: Timestamp
    seller: Seller
    currency: str
    currency_minor_unit_exponent: int
    line_items: list[LineItem]
    tax: Tax
    shipping: Shipping
    totals: Totals
    fulfillment_source: FulfillmentSource
    recurrence: Recurrence | None
    substitution_policy: SubstitutionPolicy


# --------------------------------------------------------------------- 3 ----


class ScoringStack(TypedDict):
    stack_measurement: Hash
    stack_version: int
    model_hash: Hash
    tokenizer_hash: Hash
    normalization_rules_hash: Hash
    preprocessing_hash: Hash
    quantization: str | None
    runtime_configuration_hash: Hash


class TaxonomyCategory(TypedDict):
    category_id: str
    #: Category-specific tau, in integer millionths.
    threshold_micro: int


class CategoryTaxonomy(TypedDict):
    taxonomy_id: str
    taxonomy_version: int
    categories: list[TaxonomyCategory]


class ScoringDeployment(TypedDict):
    kind: Literal["wallet-side", "gateway-side", "tee-attested"]
    enclave_measurement: Hash | None


class SemanticGate(TypedDict):
    """3.1: 'the baseline is committed, not stored ... commit(E0) = H(E0 || salt) ...
    inside the signed mandate, with the salt held by the wallet and revealed only in
    dispute', and 'the scoring stack is pinned inside the principal-signed artifact'.

    NOT IN SCOPE: E0, E1, and the distance between them are produced by a scorer this
    repository does not implement, stub, or design.
    """

    baseline_commitment: Hash
    commitment_scheme: str
    salt_disclosure_policy: Literal["dispute-only"]
    scoring_stack: ScoringStack
    #: tau in integer millionths; PROFILE-DEFINED, v1 admits integers only.
    threshold_micro: int
    category_taxonomy: CategoryTaxonomy
    threshold_selection_rule: Literal["most-conservative-matching-category"]
    aggregation: Literal["per-line-item-worst-case"]
    deployment_variant: ScoringDeployment
    cumulative_divergence_budget_micro: int
    attempt_budget: int
    cart_revision_throttle: int
    agent_visible_outcome_space: list[str]
    score_disclosure: Literal["encrypted-to-principal-and-issuer"]


class Predicate(TypedDict):
    """4.2: a predicate is patchable only when the principal owns it."""

    predicate_id: str
    kind: Literal["machine-enforceable", "semantic", "descriptive", "cumulative-budget", "freshness"]
    owner: Literal["principal", "issuer", "lender", "program", "third-party"]
    patchable: bool
    expression: dict[str, Any]
    description: str


class LineItemScore(TypedDict):
    line_id: str
    score_commitment: Hash
    exceeded_threshold: bool


class EncryptedScore(TypedDict):
    ciphertext: str
    recipients: list[Literal["principal", "issuer"]]
    encryption_alg: str


class RecordSignature(KeyBinding):
    """3.1: 'every evaluation emits a signed divergence record' - signed by the
    evaluator (wallet, gateway, or attested scorer), never by the principal."""

    signer: str
    signer_role: Literal["wallet", "gateway", "attested-scorer"]
    domain_separation: DomainSeparation
    signature: str


class DivergenceRecordDeployment(TypedDict):
    kind: Literal["wallet-side", "gateway-side", "tee-attested"]
    enclave_attestation: str | None


class DivergenceStack(TypedDict):
    stack_measurement: Hash
    stack_version: int


class DivergenceRecord(TypedDict):
    """3.1: 'every evaluation emits a signed divergence record ... appended to the mandate's lineage'."""

    schema_version: Literal["mandatepatch/divergence-record/v1"]
    record_id: str
    mandate_family_id: str
    mandate_version: int
    base_mandate_hash: Hash
    checkout_commitment: Hash
    evaluated_at: Timestamp
    deployment_variant: DivergenceRecordDeployment
    scoring_stack: DivergenceStack
    threshold_applied_micro: int
    category_id_applied: str
    aggregation: Literal["per-line-item-worst-case"]
    cart_level_score_commitment: Hash
    line_item_scores: list[LineItemScore]
    score_commitment: Hash
    encrypted_score: EncryptedScore
    outcome: Literal["pass", "suspend"]
    reason_codes: list[str]
    flagged_line_ids: list[str]
    failing_predicate_ids: list[str]
    cumulative_divergence_after_micro: int
    attempt_index: int
    previous_record_hash: Hash | None
    signature: RecordSignature


# --------------------------------------------------------------------- 4 ----


class Violation(TypedDict):
    """4.2 violation tuple.

    ``value_new`` for a semantic violation "encodes the set of approved line-item
    identifiers within the canonical commitment - approval of those exact flagged
    lines, with whole-cart approval as the degenerate all-lines case; a per-checkout
    threshold override is expressly not a permitted encoding."
    """

    violated_predicate_id: str
    value_old: Any
    value_new: Any


class MandatePatch(TypedDict):
    """4.2, field for field. No field is added and none is omitted."""

    #: "the mandate version being patched" - never another patch; patch-of-patch is prohibited.
    base_mandate_hash: Hash
    #: "monotonic within the mandate"
    patch_sequence: int
    #: "one or more (violated_predicate_id, value_old, value_new) tuples, all covered by the single human_signature below"
    violations: list[Violation]
    #: "the Section 4.3 canonical commitment"
    checkout_commitment: Hash
    #: "binds to the paused agent execution state"
    suspended_state_hash: Hash
    #: "the Section 3 signed record for the bound candidate's commitment"
    divergence_record_ref: Hash
    #: "nonce single-use per mandate family"
    nonce: str
    #: "all three enter the signed transcript"
    issued_at: Timestamp
    #: "expiry anchored to issued_at per profile TTL"
    expiry: Timestamp
    #: "optional; Section 6.3 presentation-state attestation"
    render_state_hash: NotRequired[Hash]
    #: "optional; hardware / OS-composited / software, per Section 6.3"
    attestation_tier: NotRequired[AttestationTier]
    #: "authenticator-bound; domain-separated per Section 6"
    human_signature: HumanSignature


# --------------------------------------------------------------------- 5 ----


class HeadSource(TypedDict):
    kind: Literal["transparency-log", "issuer-registry"]
    cosigned_heads: bool
    witnesses: list[str]
    operator_id: str | None
    trust_model: str


class ReBaseline(TypedDict):
    new_baseline_commitment: Hash
    commitment_scheme: str
    scoring_stack_measurement: Hash
    scoring_stack_version: int
    instruction_source_bytes_hash: Hash


class InFlightResolution(TypedDict):
    """5.1: 'the three races - authorized before, in flight at, and initiated after supersession'."""

    authorized_before: Literal["honor", "void"]
    in_flight_at: Literal["honor-within-delta", "re-evaluate-at-capture", "void"]
    initiated_after: Literal["evaluate-against-successor"]
    evaluation_points: list[str]


class ConsumeAuthority(TypedDict):
    authority_id: str
    kind: Literal["wallet", "issuer"]
    linearizable: bool


class SupersessionRecord(TypedDict):
    """5: 'Durable change is exclusively Section 5 supersession' (4.1)."""

    schema_version: Literal["mandatepatch/supersession-record/v1"]
    record_id: str
    mandate_family_id: str
    action: Literal["supersede", "revoke"]
    supersedes: Hash
    predecessor_version: int
    successor_mandate_hash: Hash | None
    successor_version: int | None
    epoch: int
    family_head: Hash
    head_source: HeadSource
    staleness_bound_seconds: int
    revocation_mode: Literal["synchronous-head-check", "bounded-staleness"]
    re_baseline: ReBaseline | None
    in_flight_resolution: InFlightResolution
    voided_patch_nullifiers: list[str]
    nullifier_epoch_update_ordering: Literal["nullify-then-advance", "advance-then-nullify", "atomic"]
    atomicity_window_ms: int
    consume_authority: ConsumeAuthority
    effective_at: Timestamp
    forced_by_patch_exhaustion: NotRequired[bool]
    full_context_redisplay: NotRequired[bool]
    cooling_off_observed_seconds: NotRequired[int]
    render_state_hash: NotRequired[Hash]
    attestation_tier: NotRequired[AttestationTier]
    human_signature: HumanSignature


# --------------------------------------------------------------- mandate ----


class SurfacedConflict(TypedDict):
    conflict_id: str
    source_excerpt: str
    interpretation_pointer: str
    note: str


class Instruction(TypedDict):
    """3.1: 'Both the immutable source bytes of the instruction and its canonical
    machine interpretation are signed at mandate creation, and material conflicts
    between them are surfaced at approval time.'
    """

    source_text: str
    source_bytes_hash: Hash
    machine_interpretation: dict[str, Any]
    machine_interpretation_hash: Hash
    surfaced_conflicts: list[SurfacedConflict]


class CumulativeScopeBudget(TypedDict):
    """4.4: 'semantic distance, monetary delta, merchant-set delta, tracked per axis'."""

    semantic_distance_micro: int
    monetary_delta_minor: int
    merchant_set_delta: int


class PatchChainGovernance(TypedDict):
    patch_of_patch_permitted: bool
    max_patches_before_forced_supersession: int
    cooling_off_seconds: int
    full_context_redisplay_required: bool
    base_locked_while_patch_pending: bool
    cumulative_scope_budget: CumulativeScopeBudget
    settled_patch_derived_spend_counts: bool


class Freshness(TypedDict):
    staleness_bound_seconds: int
    revocation_mode: Literal["synchronous-head-check", "bounded-staleness"]
    head_source: Literal["transparency-log", "issuer-registry"]
    cosigned_heads_required: bool
    evaluation_points: list[str]


class ChallengePolicy(TypedDict):
    challenge_ttl_seconds: int
    expiry_disposition: Literal["void-checkout"]
    max_outstanding_challenges: int
    max_candidates_per_challenge: int
    assurance_profile: str
    device_bound_credential_required: bool
    channel_independence_required: bool
    decline_all_is_first_class: bool


class PresentationPolicy(TypedDict):
    renderer_profile: str
    deterministic_rendering_required: bool
    neutralization_required: bool
    render_state_hash_required: bool
    minimum_attestation_tier: AttestationTier
    font_hash: Hash | None
    locale: str | None
    render_to_input_event_binding_required: bool


class Mandate(TypedDict):
    """9: 'extend those mandate formats with a small set of additional fields and one registry obligation'."""

    schema_version: Literal["mandatepatch/mandate/v1"]
    canonicalization_profile: str
    binding_profile: str
    mandate_family_id: str
    mandate_version: int
    supersedes: Hash | None
    epoch: int
    instruction: Instruction
    semantic_gate: SemanticGate
    predicates: list[Predicate]
    patch_chain_governance: PatchChainGovernance
    freshness: Freshness
    consume_authority: ConsumeAuthority
    challenge_policy: ChallengePolicy
    presentation_policy: PresentationPolicy
    issued_at: Timestamp
    expiry: Timestamp | None
    render_state_hash: NotRequired[Hash]
    attestation_tier: NotRequired[AttestationTier]
    human_signature: HumanSignature
