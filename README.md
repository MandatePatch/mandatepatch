# mandatepatch

Schemas, type stubs, and a canonical commitment function for the mandate lifecycle artifacts — MandatePatch, divergence record, supersession record — used in agent-initiated payment authorization.

## What this is

A reference implementation of the **artifact layer** described in Technical Disclosure Commons #11517, ["Mandate Lifecycle Extensions for Agentic Payment Credentials"](https://www.tdcommons.org/dpubs_series/11517) (Matt Kirby, August 2026, CC BY 4.0). The disclosure specifies five mechanisms that extend a signed payment mandate across its life: a semantic divergence gate against a committed baseline (§3), the MandatePatch (§4), supersession lineage with epoch freshness (§5), asynchronous step-up bound to a suspended execution state (§6), and presentation-state attestation (§6.3).

This repository implements the objects those mechanisms exchange, and the deterministic serialization that lets two parties hash them to the same bytes. Nothing else.

Licensed under Apache-2.0. The disclosure itself is CC BY 4.0 and separately licensed; see `NOTICE`.

A US provisional patent application (No. 64/141,321, filed 26 August 2026) precedes both the disclosure and this repository. The Apache-2.0 licence governs this code; the CC BY 4.0 licence governs the disclosure text; neither is a statement about the application.

## The artifact layer ships first

This repository defines the objects and their canonical form. It deliberately implements **no scorer, no service, and no policy engine**. Those are separable concerns and are out of scope for the reference implementation:

- **No semantic scorer.** §3's embeddings E₀ and E₁, the distance between them, and the threshold decision are produced by a pinned scoring stack this repository does not implement, stub, or design. The divergence *record* is an artifact and is in scope; the scorer that fills it in is not.
- **No service.** There is no HTTP layer, no consume authority, no nullifier store, no database. §5.3's "sole linearizable consume authority" is named in the schemas as a field, not built here.
- **No policy engine.** Predicate expressions are carried as opaque objects. Nothing here evaluates one, and §4.2's de novo re-evaluation rule is documented in schema descriptions rather than executed.
- **No renderer, no signing.** §6.3 adopts `draft-schrock-ep-presentation-binding`'s determinism and neutralization requirements by reference. Signature values in `examples/` are placeholders, not cryptographic output.

The reason for the split is practical: the artifacts are what two parties must agree on byte for byte, and they can be fixed now. Everything above them is deployment-specific.

**Status: pre-alpha. Schemas may change.** Nothing here has been through a security review, an interoperability test against a real rail, or a conformance suite.

## Schemas

JSON Schema draft 2020-12, `$id` under `https://mandatepatch.org/schemas/`. Every field carries a `description` quoting or closely paraphrasing the disclosure, with a `§` reference.

| Schema | Disclosure section | What it is |
|---|---|---|
| `schemas/mandate.schema.json` | §3, §4.4, §5.2, §6 | The base mandate: committed semantic baseline and pinned scoring stack (§3.1), the predicate set with principal/third-party ownership (§4.2), patch-chain governance (§4.4), freshness terms and Δ (§5.2), challenge and presentation policy (§6). |
| `schemas/mandate-patch.schema.json` | §4.2 | The MandatePatch, field for field. Human-signed delta against an immutable, still-live base; bound to one checkout and one suspended execution state; consumed on use; non-propagating. |
| `schemas/divergence-record.schema.json` | §3.1 | The signed per-evaluation record: score commitment, stack measurement, threshold, outcome, appended to the mandate's lineage. |
| `schemas/supersession-record.schema.json` | §5 | `supersedes = H(previous)` lineage with semantic re-baselining, epoch head, the three in-flight races, and the disclosed nullifier-to-epoch update ordering. |
| `schemas/canonical-commitment.schema.json` | §4.3 | The normative schema over which the checkout commitment is computed — the sole input to §3 scoring and the sole permissible display source for §6 challenges. |

### Constraints the schemas encode

Some rules from the disclosure are expressible in JSON Schema and are enforced; the rest live in `description` and `$comment` text. Enforced:

- `patch_of_patch_permitted` is `const: false`; `additionalProperties: false` on the patch blocks inventing a patch-of-patch reference field.
- A predicate whose `owner` is not `principal` must have `patchable: false` (§4.2: an issuer-pinned predicate "is unpatchable by the principal").
- A `supersede` action requires a successor and a `re_baseline`; a `revoke` requires both to be null (§5.1: "amendment carries semantic re-baselining — a new committed E₀ — and not merely parameter change").
- Every §4.3 field is `required`; an inapplicable value is explicit `null`, never omitted, so that "omitted-field drift is thereby within the scope of the hash."
- Every signed artifact carries `kid`, `alg`, `signed_at`, and `ds_tag` in its signature envelope, with an optional `anchor`. These are `required` because they are **not retrofittable** — see "Signature envelope" below.

Not expressible, and therefore documented rather than enforced — a verifier still has to implement them:

- Authorization under a patch is a full de novo re-evaluation of the entire predicate set.
- A `value_new` for a semantic violation encodes approved line-item identifiers within the canonical commitment. **A per-checkout threshold override is expressly not a permitted encoding** — §4.2 gives two reasons: it leaks scoring information, and it authorizes a boundary rather than a decision.
- The base mandate is locked against new authorization requests while any patch is pending.
- Supersession voids unconsumed patches against superseded versions.

`scripts/validate-schemas.py` checks the enforced ones with fifteen deliberate mutations that must be rejected.

## Signature envelope

Four of the five schemas describe **signed artifacts**: `mandate`, `mandate-patch`, `divergence-record`, `supersession-record`. (`canonical-commitment` is not one — it carries no signature member at all. It is the hash *pre-image* whose digest becomes the `checkout_commitment` those artifacts bind. Its digest is unaffected by anything on this page.)

Each signature-bearing structure carries four required members and one optional one:

| Member | | v1 |
|---|---|---|
| `kid` | required | `base64url(SHA-256(SPKI DER))`, unpadded. **Content-derived**: a key directory *resolves* a `kid`, it never *defines* one. Recorded alternative: an RFC 7638 JWK thumbprint. |
| `alg` | required | Enum: `ES256`, `ES384`, `ES512`, `EdDSA`, `RS256`, `PS256` — AP2 v0.2's ECDSA set, Ed25519, and the RSA algorithms present on deployed WebAuthn authenticators. A binding profile may narrow it; widening takes a new profile id. |
| `signed_at` | required | RFC 3339, `Z`, second precision — the same timestamp form as every other timestamp here. Deliberately **not** an epoch integer: an artifact must never carry two incompatible time conventions, and `signed_at` sits directly beside `issued_at`/`expiry`. |
| `ds_tag` | required | §6.2 domain-separator digest. See the disposition below. |
| `anchor` | **optional but recommended** | `{log_id, epoch, inclusion_proof}` against the §5.2 transparency log. Without it, `signed_at` is self-asserted — fine for routine verification, not adequate for dispute-grade evidence. Recorded alternative: an RFC 3161 timestamp authority, which a §5.2 issuer-registry deployment needs because it may run no log at all. |

**Why these are required and not optional.** A signature verifies iff `signed_at` falls inside the `[not_before, not_after]` interval recorded for `kid` — that is, **against the key current at signing time, never the key current now**. Rejecting evidence because its signing key was rotated afterwards is a bug, not a security property; planned retirement is prospective only. Without `kid`, evidence is verifiable only by trial-verification against every historical key, which goes ambiguous the instant two keys coexist. These fields cannot be added later: artifacts already signed without them can never be cleanly verified after a rotation. That is why they are present from the first commit.

### `ds_tag` disposition — decided, not left implicit

**Decision (v1):** `ds_tag` is carried **in the JSON body**, inside the signature envelope, beside the `domain_separation` components it is derived from — **and** it MUST byte-equal the domain separator bound into the carrier's signed input (the WebAuthn `clientDataJSON.challenge`, or the KB-JWT `aud`/`nonce` under an SD-JWT binding).

A verifier MUST recompute the tag from `domain_separation` **and** MUST compare it against the value bound in the carrier. A body `ds_tag` that is not reproduced in the carrier is **not covered by the signature** and MUST be rejected. The body copy is what lets evidence be checked offline without a carrier parser; the carrier copy is what makes the separator signature-covered.

**Recorded alternative:** carry the tag *entirely* in the WebAuthn/KB-JWT layer, leaving only the components in the body. Rejected for v1 on two grounds: it makes offline evidence verification depend on a carrier parser, and body components carrying no tag invite a verifier to treat them as authoritative when nothing actually signs them.

This is stated rather than left implicit because implicitness is precisely what §6.2's transplant attack needs in order to succeed — two verifiers that disagree about whether the separator is signature-covered.

**PROFILE-DEFINED derivation (v1):** SHA-256 over the ASCII prefix `MandateLifecycle/v1/transcript`, followed by `LP(purpose)`, `LP(audience)`, `LP(relying_party)`, `LP(mandate_family_id)`, `LP(decimal mandate_version)`, `LP(rail)`, `LP(binding_profile)` — where `LP(x)` is the uint16 big-endian byte length of the UTF-8 encoding of `x` followed by those bytes. Length-prefixed with **no delimiters**, because `relying_party` and `mandate_family_id` are attacker-influenced. The prefix MUST differ from §7's nullifier prefix (`MandateLifecycle/v1/nullifier`) so a transcript tag and a nullifier tag can never collide. `scripts/build-examples.py` computes this for real, so the four example artifacts carry four distinct tags — one per purpose.

## Canonicalization

§4.3 says only that "each binding profile MUST define the deterministic serialization and hash encoding that make the commitment byte-identical across parties." The disclosure deliberately fixes no serialization. This repository therefore ships **one explicitly named profile as a choice, not as a normative requirement**, and makes the profile pluggable (`registerProfile` / `register_profile`).

**Default profile: `mandatepatch/profile/v1`**

| Decision | v1 |
|---|---|
| Serialization | [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785). UCP's own AP2-mandates extension uses JCS, so this matches the ecosystem. |
| Key ordering | Lexicographic by UTF-16 code unit, per JCS §3.2.3. Python sorts on big-endian UTF-16 bytes because native code-point comparison differs above the BMP. |
| Unicode form | NFC on every key and every string value. Lone surrogates are rejected, not replaced. Keys that collide only after NFC reject the whole document. |
| Numbers | **Integers only, everywhere, in every artifact.** Money is integer minor units; tax rates are integer basis points; semantic distances are integer millionths (τ = 0.18 is `threshold_micro: 180000`). Range is the exactly-representable IEEE-754 integer range. |
| Array ordering | `line_items` is sorted ascending by `(sku, variant_id, line_id)` under UTF-16 ordering, and only in the commitment function. Every other array is order-significant and preserved. |
| Hash | SHA-256 over the UTF-8 bytes of the canonical string, base64url without padding, prefixed: `sha-256:<43 chars>`. |
| Field presence | Explicit `null` over omission throughout the §4.3 schema. |

The integers-only rule is the load-bearing choice. RFC 8785 requires ECMAScript `Number::toString` for numbers, which is exact but awkward to reproduce identically outside a JavaScript engine; admitting no non-integer number removes the entire class of cross-language float-formatting divergence. A future profile that needs non-integer numbers must specify `Number::toString` exactly.

### Open decisions the disclosure leaves to the profile

Every one is marked `PROFILE-DEFINED:` in the source or schema text. `v1` takes a position on the first group and takes none on the second.

*Taken by v1:* serialization and hash encoding (§4.3); numeric encoding; Unicode form; line-item array ordering; explicit-null-over-omission; hash string format; the timestamp form (RFC 3339, `Z`, second precision, everywhere including `signed_at`); the `kid` derivation; the `alg` enum; the `ds_tag` disposition and derivation (§6.2); the time anchor's reuse of the §5.2 log.

*Left open by v1 — a deployment must choose:* the commitment construction for `commit(E₀)` (§3.1 fixes the properties, not the construction); the embedding distance function and its range (§3.1); the category taxonomy vocabulary (§3.1); the machine-interpretation vocabulary (§3.1); the predicate expression language (§4.2); `value_old` disclosure policy and its commitment scheme (§4.2); nonce encoding and nullifier derivation (§4.2, §7); patch TTL (§4.2); the forced-supersession patch ceiling and the cooling-off interval, which §4.4 calls "a low, profile-defined mandatory number" and "a profile-defined cooling-off interval"; Δ (§5.2); the in-flight resolution chosen for each of the three races, and the nullifier-to-epoch update ordering — §5.1 requires that these be deterministic and disclosed, not that they take a particular value; challenge TTL and caps (§6); the assurance-tier vocabulary (§6.2); the renderer identifier and the composited-interface canonicalization for `render_state_hash` (§6.3); the reason-code vocabulary (§3.1); the encryption construction for the encrypted score (§3.1); the key directory's location and format, and the compromise-window semantics, which are governance rather than schema; the carrier for the principal signature (WebAuthn vs. SD-JWT KB-JWT), which `ds_tag` is written to accommodate either way.

### Byte-identity

The TypeScript and Python ports must produce identical output. `examples/canonicalization-vectors.json` is the shared vector file — 12 accept vectors and 4 reject vectors, including UTF-16 versus code-point key ordering above the BMP, NFC normalization, JCS escaping, integer edge cases, and line-item reordering. Both CI jobs check against the frozen expected values, and a third job diffs the two ports' computed output directly.

```
$ bash scripts/parity.sh
PASS  typescript: 12 accept + 4 reject vectors, profile mandatepatch/profile/v1
PASS  python: 12 accept + 4 reject vectors, profile mandatepatch/profile/v1
PASS  typescript and python produced byte-identical output
```

## Usage

TypeScript:

```ts
import { canonicalCommitment, digest } from "mandatepatch";

const { canonical, digest: checkoutCommitment } = canonicalCommitment(cart);
// checkoutCommitment -> "sha-256:2NCnJrP9XA_Ax0pnVLy1tT6nFmxECDvLQ0ueKJwe1V0"
// `canonical` is the sole input to §3 scoring and the sole display source for §6.

const baseMandateHash = digest(mandate);
```

Python:

```python
from mandatepatch import canonical_commitment, digest

out = canonical_commitment(cart)
checkout_commitment = out["digest"]
base_mandate_hash = digest(mandate)
```

## Examples

`examples/` carries one valid instance per schema, using the disclosure's own worked example (§1): a standing weekly grocery mandate naming a twelve-pack; one week only a twenty-four-pack is in stock; the cart passes every machine-enforceable constraint and diverges only in meaning. The instances cross-reference each other by real hash — the divergence record binds the commitment, the patch binds the divergence record and the mandate version, the supersession record binds the predecessor — and are regenerated by `scripts/build-examples.py` rather than hand-maintained.

**Signature and ciphertext values in `examples/` are placeholders.** This repository ships no signing, verification, or encryption code. Merchant and product names are fictitious.

## Verifying

```bash
bash scripts/validate-examples.sh   # ajv, draft 2020-12, every example against its schema
python3 scripts/validate-schemas.py # positive cases plus 15 mutations that must be rejected
bash scripts/parity.sh              # TS and Python vectors, then a byte-for-byte diff
```

`.github/workflows/ci.yml` runs all three plus `tsc --noEmit`, `ruff`, and `mypy`.

## Layout

```
schemas/    JSON Schema draft 2020-12, one file per artifact
ts/         TypeScript port: types, canonicalization, vector runner
python/     Python port: TypedDicts, canonicalization, vector runner
examples/   one valid instance per schema, plus the shared canonicalization vectors
scripts/    generators for examples and vectors; the three verification entry points
```

## What this is not

- Not a payment product, an agent, or a wallet.
- Not an implementation of AP2, Verifiable Intent, ACP, or the Trusted Agent Protocol. The disclosure's §9 sketches bindings to those; none is implemented here.
- Not a claim of conformance to any network specification, and not endorsed by any payment network or standards body.
- Not legal or compliance advice.
- Not a security-reviewed artifact.

## Citation

> Matt Kirby, "Mandate Lifecycle Extensions for Agentic Payment Credentials", Technical Disclosure Commons, Defensive Publications Series #11517, August 2026. https://www.tdcommons.org/dpubs_series/11517

The disclosure was published to keep this layer open. Its own words: "the lifecycle of a payment mandate — its drift, its amendment, its supersession, and its proof — should be common infrastructure, not a chokepoint."
