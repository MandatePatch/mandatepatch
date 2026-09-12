/**
 * Type stubs mirroring `schemas/*.schema.json`.
 *
 * These are shapes only. This repository ships the artifact layer: it defines the
 * objects and their canonical form, and implements no scorer, no service, and no
 * policy engine. Nothing here evaluates a predicate, computes an embedding,
 * consumes a nullifier, or renders a challenge.
 *
 * Section references are to Technical Disclosure Commons #11517, "Mandate Lifecycle
 * Extensions for Agentic Payment Credentials" (Matt Kirby, CC-BY).
 */

/** `sha-256:<base64url-unpadded>` under `mandatepatch/profile/v1`. PROFILE-DEFINED encoding. */
export type Hash = string;

/** RFC 3339 date-time. */
export type Timestamp = string;

/** §6.3: "hardware secure-display, OS-composited, software", the last "declared evidentially weak". */
export type AttestationTier = "hardware" | "os-composited" | "software";

/** §6.2: "domain-separated over audience, relying party, mandate family and version, rail, and protocol purpose". */
export interface DomainSeparation {
  audience: string;
  relying_party: string;
  mandate_family_id: string;
  mandate_version: number;
  rail: string;
  purpose: string;
}

/** §6.2: assurance profiles are "named tiers of authenticator strength and channel independence". */
export interface Authenticator {
  credential_id: string;
  kind: string;
  device_bound: boolean;
  channel_independent: boolean;
}

/**
 * PROFILE-DEFINED: profile v1's algorithm suite. ES256/ES384/ES512 is the ECDSA set
 * AP2 v0.2 requires of its bindings; EdDSA is Ed25519; RS256/PS256 appear on deployed
 * WebAuthn authenticators. A binding profile MAY narrow this union; widening it takes
 * a new profile identifier.
 */
export type SignatureAlg = "ES256" | "ES384" | "ES512" | "EdDSA" | "RS256" | "PS256";

/**
 * Independent evidence that a signature existed at its `signed_at`.
 *
 * PROFILE-DEFINED: profile v1 anchors into the §5.2 transparency log rather than
 * standing up a second one — §5.2 already requires "cosigned heads or a witness
 * network against split-view equivocation", which is exactly what a time anchor
 * needs. The recorded alternative is an RFC 3161 timestamp authority, which a §5.2
 * issuer-registry deployment needs instead because it may run no log at all.
 *
 * Optional but RECOMMENDED: omit it and `signed_at` is self-asserted, which is fine
 * for routine verification and not adequate for dispute-grade evidence.
 */
export interface Anchor {
  log_id: string;
  epoch: number;
  /** Merkle audit path, leaf-ward to root-ward, base64url unpadded. */
  inclusion_proof: string[];
}

/**
 * The envelope fields every signed artifact carries so that its signature remains
 * verifiable across key rotation.
 *
 * A signature verifies iff `signed_at` falls inside the [not_before, not_after]
 * interval recorded for `kid` — that is, against THE KEY CURRENT AT SIGNING TIME,
 * never the key current now. Rejecting evidence because its key was later rotated
 * is a bug, not a security property.
 *
 * These are not retrofittable. Evidence signed without them is verifiable only by
 * trial-verification against every historical key, which goes ambiguous the instant
 * two keys coexist — which is why they are present from the first commit.
 */
export interface KeyBinding {
  /** `base64url(SHA-256(SPKI DER))`, unpadded. Content-derived: a directory resolves a kid, it never defines one. */
  kid: string;
  alg: SignatureAlg;
  /** RFC 3339, "Z", second precision — the same timestamp form as every other timestamp here. */
  signed_at: Timestamp;
  /**
   * §6.2 domain-separator digest. PROFILE-DEFINED, DECIDED: profile v1 carries the tag
   * in the JSON body AND requires it to byte-equal the separator bound into the
   * carrier's signed input (WebAuthn `clientDataJSON.challenge`, or KB-JWT `aud`/`nonce`).
   * The body copy makes evidence checkable offline; the carrier copy is what makes the
   * separator signature-covered. Recorded alternative: carrier-only, rejected for v1.
   */
  ds_tag: string;
  anchor?: Anchor;
}

/** §4.2: "authenticator-bound; domain-separated per Section 6". */
export interface HumanSignature extends KeyBinding {
  authenticator: Authenticator;
  assurance_profile: string;
  domain_separation: DomainSeparation;
  signature: string;
}

/** §3.1: "every evaluation emits a signed divergence record" — signed by the evaluator, not the principal. */
export interface RecordSignature extends KeyBinding {
  signer: string;
  signer_role: "wallet" | "gateway" | "attested-scorer";
  domain_separation: DomainSeparation;
  signature: string;
}

/* ------------------------------------------------------------------ §4.3 ---- */

export interface FulfillmentSource {
  kind: "ship-from-warehouse" | "ship-from-store" | "pickup" | "marketplace-seller" | "digital";
  location_id: string | null;
  marketplace_seller_id: string | null;
}

export interface LineItem {
  line_id: string;
  sku: string;
  variant_id: string | null;
  title: string;
  quantity: number;
  unit_amount_minor: number;
  total_amount_minor: number;
  fulfillment_source: FulfillmentSource;
}

export interface TaxComponent {
  kind: string;
  jurisdiction: string;
  rate_basis_points: number;
  amount_minor: number;
}

export interface Recurrence {
  interval: "day" | "week" | "month" | "year";
  interval_count: number;
  occurrences: number | null;
  until: Timestamp | null;
  first_charge_at: Timestamp;
  amount_variability: "fixed" | "variable";
  max_amount_minor: number | null;
}

export interface SubstitutionPolicy {
  mode: "none" | "equivalent-only" | "enumerated" | "merchant-discretion";
  allowed_substitutions: Array<{ line_id: string; sku: string; variant_id: string | null }>;
  max_unit_amount_delta_minor: number | null;
  notify_principal: boolean;
}

/**
 * §4.3: "seller identity, line items with SKU and variant identifiers, quantities,
 * unit and total amounts, currency, tax, shipping, fulfillment source, recurrence
 * terms, and post-authorization substitution policy." Also "the sole input to
 * Section 3 scoring and the sole permissible display source for Section 6 challenges."
 */
export interface CanonicalCommitment {
  profile: string;
    checkout_id: string;   
  /** §4.3 (v2.3 erratum): 16-byte attempt distinguisher; required. */   
  attempt_nonce: string;
  created_at: Timestamp;
  seller: {
    seller_id: string;
    legal_name: string;
    merchant_category_code: string | null;
    domain: string | null;
  };
  currency: string;
  currency_minor_unit_exponent: number;
  line_items: LineItem[];
  tax: { total_amount_minor: number; inclusive: boolean; components: TaxComponent[] };
  shipping: {
    amount_minor: number;
    method: string | null;
    destination: {
      country: string | null;
      region: string | null;
      postal_code: string | null;
      address_commitment: Hash | null;
    };
  };
  totals: {
    subtotal_minor: number;
    tax_minor: number;
    shipping_minor: number;
    discount_minor: number;
    grand_total_minor: number;
  };
  fulfillment_source: FulfillmentSource;
  recurrence: Recurrence | null;
  substitution_policy: SubstitutionPolicy;
}

/* -------------------------------------------------------------------- §3 ---- */

export interface ScoringStack {
  stack_measurement: Hash;
  stack_version: number;
  model_hash: Hash;
  tokenizer_hash: Hash;
  normalization_rules_hash: Hash;
  preprocessing_hash: Hash;
  quantization: string | null;
  runtime_configuration_hash: Hash;
}

/**
 * §3.1: "the baseline is committed, not stored ... commit(E0) = H(E0 || salt) ...
 * inside the signed mandate, with the salt held by the wallet and revealed only in
 * dispute", and "the scoring stack is pinned inside the principal-signed artifact".
 *
 * NOT IN SCOPE: E0, E1, and the distance between them are produced by a scorer this
 * repository does not implement, stub, or design.
 */
export interface SemanticGate {
  baseline_commitment: Hash;
  commitment_scheme: string;
  salt_disclosure_policy: "dispute-only";
  scoring_stack: ScoringStack;
  /** τ in integer millionths; PROFILE-DEFINED, v1 admits integers only. */
  threshold_micro: number;
  category_taxonomy: {
    taxonomy_id: string;
    taxonomy_version: number;
    categories: Array<{ category_id: string; threshold_micro: number }>;
  };
  threshold_selection_rule: "most-conservative-matching-category";
  aggregation: "per-line-item-worst-case";
  deployment_variant: {
    kind: "wallet-side" | "gateway-side" | "tee-attested";
    enclave_measurement: Hash | null;
  };
  cumulative_divergence_budget_micro: number;
  attempt_budget: number;
  cart_revision_throttle: number;
  agent_visible_outcome_space: ["pass", "suspend"];
  score_disclosure: "encrypted-to-principal-and-issuer";
}

/** §4.2: a predicate is patchable only when the principal owns it. */
export interface Predicate {
  predicate_id: string;
  kind: "machine-enforceable" | "semantic" | "descriptive" | "cumulative-budget" | "freshness";
  owner: "principal" | "issuer" | "lender" | "program" | "third-party";
  patchable: boolean;
  expression: Record<string, unknown>;
  description: string;
}

/** §3.1: "every evaluation emits a signed divergence record ... appended to the mandate's lineage". */
export interface DivergenceRecord {
  schema_version: "mandatepatch/divergence-record/v1";
  record_id: string;
  mandate_family_id: string;
  mandate_version: number;
  base_mandate_hash: Hash;
  checkout_commitment: Hash;
  evaluated_at: Timestamp;
  deployment_variant: {
    kind: "wallet-side" | "gateway-side" | "tee-attested";
    enclave_attestation: string | null;
  };
  scoring_stack: { stack_measurement: Hash; stack_version: number };
  threshold_applied_micro: number;
  category_id_applied: string;
  aggregation: "per-line-item-worst-case";
  cart_level_score_commitment: Hash;
  line_item_scores: Array<{ line_id: string; score_commitment: Hash; exceeded_threshold: boolean }>;
  score_commitment: Hash;
  encrypted_score: {
    ciphertext: string;
    recipients: Array<"principal" | "issuer">;
    encryption_alg: string;
  };
  outcome: "pass" | "suspend";
  reason_codes: string[];
  flagged_line_ids: string[];
  failing_predicate_ids: string[];
  cumulative_divergence_after_micro: number;
  attempt_index: number;
  previous_record_hash: Hash | null;
  signature: RecordSignature;
}

/* -------------------------------------------------------------------- §4 ---- */

/**
 * §4.2 violation tuple.
 *
 * `value_new` for a semantic violation "encodes the set of approved line-item
 * identifiers within the canonical commitment - approval of those exact flagged
 * lines, with whole-cart approval as the degenerate all-lines case; a per-checkout
 * threshold override is expressly not a permitted encoding."
 */
export interface Violation {
  violated_predicate_id: string;
  value_old: unknown;
  value_new: unknown;
}

/** §4.2, field for field. No field is added and none is omitted. */
export interface MandatePatch {
  /** "the mandate version being patched" - never another patch; patch-of-patch is prohibited. */
  base_mandate_hash: Hash;
  /** "monotonic within the mandate" */
  patch_sequence: number;
  /** "one or more (violated_predicate_id, value_old, value_new) tuples, all covered by the single human_signature below" */
  violations: Violation[];
  /** "the Section 4.3 canonical commitment" */
  checkout_commitment: Hash;
  /** "binds to the paused agent execution state" */
  suspended_state_hash: Hash;
  /** "the Section 3 signed record for the bound candidate's commitment" */
  divergence_record_ref: Hash;
  /** "nonce single-use per mandate family" */
  nonce: string;
  /** "all three enter the signed transcript" */
  issued_at: Timestamp;
  /** "expiry anchored to issued_at per profile TTL" */
  expiry: Timestamp;
  /** "optional; Section 6.3 presentation-state attestation" */
  render_state_hash?: Hash;
  /** "optional; hardware / OS-composited / software, per Section 6.3" */
  attestation_tier?: AttestationTier;
  /** "authenticator-bound; domain-separated per Section 6" */
  human_signature: HumanSignature;
}

/* -------------------------------------------------------------------- §5 ---- */

/** §5: "Durable change is exclusively Section 5 supersession" (§4.1). */
export interface SupersessionRecord {
  schema_version: "mandatepatch/supersession-record/v1";
  record_id: string;
  mandate_family_id: string;
  action: "supersede" | "revoke";
  supersedes: Hash;
  predecessor_version: number;
  successor_mandate_hash: Hash | null;
  successor_version: number | null;
  epoch: number;
  family_head: Hash;
  head_source: {
    kind: "transparency-log" | "issuer-registry";
    cosigned_heads: boolean;
    witnesses: string[];
    operator_id: string | null;
    trust_model: string;
  };
  staleness_bound_seconds: number;
  revocation_mode: "synchronous-head-check" | "bounded-staleness";
  /** §5.1: "amendment carries semantic re-baselining - a new committed E0". */
  re_baseline: {
    new_baseline_commitment: Hash;
    commitment_scheme: string;
    scoring_stack_measurement: Hash;
    scoring_stack_version: number;
    instruction_source_bytes_hash: Hash;
  } | null;
  /** §5.1: "the three races - authorized before, in flight at, and initiated after supersession". */
  in_flight_resolution: {
    authorized_before: "honor" | "void";
    in_flight_at: "honor-within-delta" | "re-evaluate-at-capture" | "void";
    initiated_after: "evaluate-against-successor";
    evaluation_points: ["authorization", "capture"];
  };
  voided_patch_nullifiers: string[];
  nullifier_epoch_update_ordering: "nullify-then-advance" | "advance-then-nullify" | "atomic";
  atomicity_window_ms: number;
  consume_authority: { authority_id: string; kind: "wallet" | "issuer"; linearizable: true };
  effective_at: Timestamp;
  forced_by_patch_exhaustion?: boolean;
  full_context_redisplay?: boolean;
  cooling_off_observed_seconds?: number;
  render_state_hash?: Hash;
  attestation_tier?: AttestationTier;
  human_signature: HumanSignature;
}

/* -------------------------------------------------------------- mandate ---- */

/** §9: "extend those mandate formats with a small set of additional fields and one registry obligation". */
export interface Mandate {
  schema_version: "mandatepatch/mandate/v1";
  canonicalization_profile: string;
  binding_profile: string;
  mandate_family_id: string;
  mandate_version: number;
  supersedes: Hash | null;
  epoch: number;
  instruction: {
    source_text: string;
    source_bytes_hash: Hash;
    machine_interpretation: Record<string, unknown>;
    machine_interpretation_hash: Hash;
    surfaced_conflicts: Array<{
      conflict_id: string;
      source_excerpt: string;
      interpretation_pointer: string;
      note: string;
    }>;
  };
  semantic_gate: SemanticGate;
  predicates: Predicate[];
  patch_chain_governance: {
    patch_of_patch_permitted: false;
    max_patches_before_forced_supersession: number;
    cooling_off_seconds: number;
    full_context_redisplay_required: true;
    base_locked_while_patch_pending: true;
    cumulative_scope_budget: {
      semantic_distance_micro: number;
      monetary_delta_minor: number;
      merchant_set_delta: number;
    };
    settled_patch_derived_spend_counts: true;
  };
  freshness: {
    staleness_bound_seconds: number;
    revocation_mode: "synchronous-head-check" | "bounded-staleness";
    head_source: "transparency-log" | "issuer-registry";
    cosigned_heads_required: boolean;
    evaluation_points: ["authorization", "capture"];
  };
  consume_authority: { authority_id: string; kind: "wallet" | "issuer"; linearizable: true };
  challenge_policy: {
    challenge_ttl_seconds: number;
    expiry_disposition: "void-checkout";
    max_outstanding_challenges: number;
    max_candidates_per_challenge: number;
    assurance_profile: string;
    device_bound_credential_required: boolean;
    channel_independence_required: boolean;
    decline_all_is_first_class: true;
  };
  presentation_policy: {
    renderer_profile: string;
    deterministic_rendering_required: true;
    neutralization_required: true;
    render_state_hash_required: boolean;
    minimum_attestation_tier: AttestationTier;
    font_hash: Hash | null;
    locale: string | null;
    render_to_input_event_binding_required: true;
  };
  issued_at: Timestamp;
  expiry: Timestamp | null;
  render_state_hash?: Hash;
  attestation_tier?: AttestationTier;
  human_signature: HumanSignature;
}
