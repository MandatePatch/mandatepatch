## v0.1.2 — errata alignment, verified (2026-08-28)

Completes the v0.1.1 errata work. v0.1.1 declared the new field but shipped without
exercising it; this release makes the change testable and the build reproducible.

- **`attempt_nonce` is now exercised, not just declared.** v0.1.1 added it to
  `canonical-commitment.schema.json` as REQUIRED but did not update the example instance
  or the vectors, so the repo's own suite failed on its positive case and no test could
  distinguish the erratum from its absence. The example generator now emits the field,
  and a new canonicalization vector, `commitment-attempt-nonce-distinguishes`, is
  byte-identical to `commitment-canonical-order` in every other field — same seller, same
  line items, same totals, same `checkout_id` — so a matching digest between those two
  vectors means the erratum has been silently reverted.
- **New schema mutation** `commitment-missing-attempt-nonce` asserts the field is required
  rather than optional. Mutation suite: 15 → 16.
- **`validate-schemas.py` summary line is now computed.** It previously printed the counts
  `5 examples valid, 15 mutations rejected` as a hardcoded literal, so the number in CI
  output was decorative and did not track the suite. It is now derived from the data.
- **tsconfig fix.** `ignoreDeprecations: "6.0"` is not a valid value for the pinned
  TypeScript (`^5.7.2`, resolving to 5.9.x) and failed the build with `TS5103`; corrected
  to `"5.0"`. This was a compile error, not a missing dev dependency — `npm install` did
  not resolve it, and CI would have gone red on first push.

**Parity digest:** `b9b75ff31b16a016c947c714f1c7d9f664e623d6668be3799f5a72527933a0e4`
(13 accept + 4 reject vectors, TypeScript and Python byte-identical).
Supersedes `563962e9…`, which corresponds to the pre-errata field set.

## v0.1.1 — v2.3 errata alignment (2026-08-28) — withdrawn, unreleased
- `attempt_nonce` added to the canonical commitment as a REQUIRED per-attempt distinguisher
  (§4.3, v2.3 erratum) — distinct from `checkout_id`, which persists across cart mutations.
- tsconfig: `ignoreDeprecations` for TS7 toolchains.

Withdrawn before publication: the schema change was not carried into the example instance
or the vectors, and the tsconfig value was invalid for the pinned compiler. Superseded by
v0.1.2. Recorded here rather than deleted, because the failure mode — a required field
added to a schema without a test that can observe it — is the kind this project exists to
make visible.
