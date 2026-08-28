## v0.1.4 — version-string invariant observed in CI (2026-08-28)

`python/mandatepatch/__init__.py` declared `__version__ = "0.0.1"` while
`python/pyproject.toml` and `ts/package.json` declared `0.1.3`. Nothing in the
suite compared the three sources, so the disagreement was unobservable — the
same failure mode that withdrew v0.1.1.

- All three sources now declare `0.1.4`. Writing `0.1.3` into `__init__.py`
  would have asserted that the v0.1.3 tree carried that string. It did not.
- `scripts/check-versions.py` reads the three sources with the stdlib only
  (`tomllib`, `json`, `re`) and exits 1 if they differ.
- The `schema validation` job runs the checker before schema work. A committed
  checker that CI never invokes is not a check.
- `ts/package.json` repository URL case corrected to `MandatePatch/mandatepatch`.
  No version export exists in `ts/src`; a fourth source was not invented.

**Parity digest:** `b9b75ff31b16a016c947c714f1c7d9f664e623d6668be3799f5a72527933a0e4`
- unchanged from v0.1.2 / v0.1.3. Canonicalization, schemas, vectors, and
  examples were not touched.

## v0.1.3 — CI reproducibility (2026-08-28)

First push went red. Both failures were environment assumptions, not defects in the
artifacts: the suite passed locally only because the machine it was verified on had
been primed by the build that produced it.

- **`scripts/validate-examples.sh` now fetches the plugin it uses.** It invoked
  `npx --yes ajv-cli@5 ... -c ajv-formats`, which fetches ajv-cli only and then asks
  it to load a plugin that was never fetched. It passed on any machine with
  `ajv-formats` installed globally and failed everywhere else. Now
  `npx --yes -p ajv-cli@5 -p ajv-formats ajv validate ...`, which carries its own
  dependencies.
- **Ruff rule selection is explicit.** `[tool.ruff]` set only `line-length` and
  `target-version`, leaving the rule set to ruff's defaults - which are not stable
  across releases. CI installed a ruff whose defaults include `UP` and `RUF`; the
  local machine had one whose defaults did not. Same code, same command, 0 errors
  here and 65 there. `[tool.ruff.lint] select` now names the rules.
- **The 65 findings were fixed, not silenced.** They were correct for a Python 3.11
  target: `typing.Dict/List/Tuple` to builtins (28), `Optional[X]` to `X | None` (28),
  `Callable` from `collections.abc`, `__all__` sorted, one printf format to an f-string.
  The last of these is in the RFC 8785 string-escaping path, so the parity digest was
  re-derived after the change and is **unchanged**, confirming the edits were syntactic.
- **ruff, mypy and jsonschema are pinned to exact versions** in `ci.yml`. Unpinned
  linters mean CI behavior changes when upstream releases, which is the wrong default
  anywhere and a contradiction in a repository whose claim is reproducibility.

**Parity digest:** `b9b75ff31b16a016c947c714f1c7d9f664e623d6668be3799f5a72527933a0e4`
- unchanged from v0.1.2. No artifact, schema, vector or canonicalization behavior
changed in this release.

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
