# examples

One valid instance per schema, plus the shared canonicalization test vectors.

The scenario is the disclosure's own worked example (§1): a standing weekly grocery
mandate that names a twelve-pack of a soft drink and caps spend at $150; one week the
store's only stock is a twenty-four-pack. The cart passes every machine-enforceable
constraint — right merchant, within budget — and diverges only in meaning.

| File | Schema | Notes |
|---|---|---|
| `canonical-commitment.example.json` | `canonical-commitment.schema.json` | §4.3. Its digest is `sha-256:2NCnJrP9XA_Ax0pnVLy1tT6nFmxECDvLQ0ueKJwe1V0` under `mandatepatch/profile/v1`. |
| `mandate.example.json` | `mandate.schema.json` | v1 of the family. Predicate `pred-issuer-category-restriction` is issuer-owned and therefore `patchable: false`. |
| `divergence-record.example.json` | `divergence-record.schema.json` | Outcome `suspend`; line `li-002` flagged; the score is committed and encrypted, never disclosed in the record. |
| `mandate-patch.example.json` | `mandate-patch.schema.json` | `value_new` is `{"approved_line_ids": ["li-002"]}` — approval of that exact flagged line. A threshold override would not be a permitted encoding. |
| `supersession-record.example.json` | `supersession-record.schema.json` | The durable follow-up: v1 → v2 with a new committed E₀, epoch 2, and the outstanding patch nullifier voided. |
| `canonicalization-vectors.json` | — | Shared TS/Python test vectors. Not an instance of any schema. |

Regenerate with `python3 scripts/build-examples.py` then `python3 scripts/build-vectors.py`.
Cross-references between the files are real hashes computed by the profile, so hand-editing
one file will break the others.

**Signature and ciphertext values are placeholders.** This repository ships no signing,
verification, or encryption code. Merchant and product names are fictitious.

**But the signature-envelope values are real.** `ds_tag` is genuinely computed by
`build-examples.py` from the `domain_separation` components beside it, using profile v1's
length-prefixed derivation — which is why the four artifacts carry four *different* tags,
one per `purpose`, exactly as §6.2's transplant resistance requires. `kid` and
`anchor.inclusion_proof` are reproducible SHA-256 digests of labelled placeholder inputs:
the key material is fictitious, but the derivation shape, the base64url encoding, and the
43-character unpadded length are precisely what profile v1 mandates.

The `anchor` member is present on `mandate-patch` and `divergence-record` — the two
artifacts §4.4 calls "the dispute-evidence bundle" — and deliberately absent from
`mandate` and `supersession-record`, so the example set exercises both the present and
the absent case of an optional field.
