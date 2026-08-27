# Contributing

This repository is the artifact layer for Technical Disclosure Commons #11517, ["Mandate Lifecycle Extensions for Agentic Payment Credentials"](https://www.tdcommons.org/dpubs_series/11517). Contributions are welcome; the scope is narrow on purpose.

## Scope

**In scope:** schema corrections, additional binding profiles, additional canonicalization test vectors, ports to other languages, bindings to AP2 / Verifiable Intent / ACP mandate formats, documentation that makes a `PROFILE-DEFINED:` decision easier to make.

**Out of scope, and a PR adding one will be closed:** a semantic scorer or any embedding/divergence scoring code; an HTTP service, consume authority, or nullifier store; a policy or predicate-expression engine; a renderer; signing or verification code. These are separable, deployment-specific, and deliberately absent. See "The artifact layer ships first" in the README.

If a change starts adding business logic, it has left scope.

## Ground rules for schema changes

1. **Every field carries a `description` that quotes or closely paraphrases the disclosure, with a `§` reference.** A field that cannot be traced to a section is probably an invention; say so explicitly in the PR if it is one, and say why it is needed.
2. **`mandate-patch.schema.json` mirrors §4.2 field for field.** Do not add fields to it and do not remove fields from it. Structure inside `violations[]` follows §4.2's `(violated_predicate_id, value_old, value_new)` tuple.
3. **Encode a constraint in the schema where JSON Schema can express it, in `description` text where it cannot.** If you move a rule from prose into a constraint, add a mutation to `scripts/validate-schemas.py` that proves it is enforced.
4. **Mark every place the disclosure leaves a choice open with a `PROFILE-DEFINED:` comment naming the open decision**, and add it to the README's open-decisions list.
5. A schema change is a breaking change while the project is pre-alpha. Say so in the PR.

## Ground rules for canonicalization changes

Profile `mandatepatch/profile/v1` is frozen in behaviour. A change to how it serializes or hashes changes every commitment ever computed under it, which is exactly the failure the profile exists to prevent.

- Fixing a bug where a port disagrees with RFC 8785 is a `v1` fix.
- Changing a `PROFILE-DEFINED` decision is a **new profile** (`mandatepatch/profile/v2`, or a binding-specific id), registered alongside v1, not an edit to v1.
- Any change to the canonicalization code must keep the TypeScript and Python ports byte-identical. `bash scripts/parity.sh` must pass, and it diffs the two ports' computed output directly rather than trusting either one.
- New vectors go in `examples/canonicalization-vectors.json` via `python3 scripts/build-vectors.py`. Do not hand-edit the expected values.

## Adding a binding profile

Implement `CanonicalizationProfile` in both ports and register it. A profile must state, in its own documentation, every decision listed under "Open decisions the disclosure leaves to the profile" in the README that it takes a position on. §4.3 requires only that the serialization and hash encoding be deterministic and byte-identical across parties; it does not require anyone to use v1.

## Regenerating

```bash
python3 scripts/build-examples.py   # regenerate examples/*.example.json with real cross-referenced hashes
python3 scripts/build-vectors.py    # regenerate examples/canonicalization-vectors.json
```

Run `build-examples.py` before `build-vectors.py`; the vectors read the commitment example.

## Verifying before you open a PR

```bash
bash scripts/validate-examples.sh
python3 scripts/validate-schemas.py
bash scripts/parity.sh
cd ts && npx tsc -p tsconfig.json --noEmit
```

## Licensing and provenance

Code contributions are under Apache-2.0. Schema `description` text quotes the disclosure, which is CC BY 4.0; keep the attribution in `NOTICE` intact and do not strip the `§` references, since they are what makes a quote traceable.

Do not add a dependency without saying why in the PR. Both ports are currently dependency-free at runtime: the Python package uses only the standard library, and the TypeScript package uses only `node:crypto`.

## Reporting a problem

Open an issue. If the problem is that two implementations disagree on a commitment, include both canonical strings — not just the digests — and the input that produced them.
