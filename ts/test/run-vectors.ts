/**
 * Recompute every vector in examples/canonicalization-vectors.json, assert the
 * frozen expected values byte for byte, and emit this port's computed output so
 * the CI parity job can diff it against the Python port's.
 *
 * Usage: node dist/test/run-vectors.js [--emit <path>]
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { CanonicalizationError, canonicalCommitment, canonicalize, digest } from "../src/canonicalize";

interface Vector {
  name: string;
  mode: "value" | "commitment";
  input: unknown;
  expected_jcs: string;
  expected_digest: string;
}
interface Reject {
  name: string;
  mode: "value" | "commitment";
  input: unknown;
  expected_error_code: string;
}

// Walk up from wherever this file was compiled to until the repository root is found.
function repoRoot(): string {
  let dir = __dirname;
  for (let i = 0; i < 6; i++) {
    if (existsSync(resolve(dir, "examples", "canonicalization-vectors.json"))) return dir;
    dir = resolve(dir, "..");
  }
  throw new Error("could not locate examples/canonicalization-vectors.json above " + __dirname);
}

const root = repoRoot();
const vectorsPath = resolve(root, "examples", "canonicalization-vectors.json");
const doc = JSON.parse(readFileSync(vectorsPath, "utf8")) as {
  profile: string;
  vectors: Vector[];
  rejects: Reject[];
};

const emitIndex = process.argv.indexOf("--emit");
const emitPath = emitIndex >= 0 ? process.argv[emitIndex + 1] : null;

const computed: Array<Record<string, string>> = [];
const failures: string[] = [];

for (const v of doc.vectors) {
  let jcs: string;
  let dg: string;
  if (v.mode === "commitment") {
    const out = canonicalCommitment(v.input);
    jcs = out.canonical;
    dg = out.digest;
  } else {
    jcs = canonicalize(v.input);
    dg = digest(v.input);
  }
  computed.push({ name: v.name, jcs, digest: dg });
  if (jcs !== v.expected_jcs) {
    failures.push(`${v.name}: jcs mismatch\n  expected ${JSON.stringify(v.expected_jcs)}\n  actual   ${JSON.stringify(jcs)}`);
  }
  if (dg !== v.expected_digest) {
    failures.push(`${v.name}: digest mismatch\n  expected ${v.expected_digest}\n  actual   ${dg}`);
  }
}

for (const r of doc.rejects) {
  let code = "<no error raised>";
  try {
    if (r.mode === "commitment") canonicalCommitment(r.input);
    else canonicalize(r.input);
  } catch (err) {
    code = err instanceof CanonicalizationError ? err.code : `<${(err as Error).name}>`;
  }
  computed.push({ name: r.name, error_code: code });
  if (code !== r.expected_error_code) {
    failures.push(`${r.name}: error mismatch\n  expected ${r.expected_error_code}\n  actual   ${code}`);
  }
}

if (emitPath) {
  writeFileSync(emitPath, JSON.stringify(computed, null, 2) + "\n", "utf8");
}

const total = doc.vectors.length + doc.rejects.length;
if (failures.length > 0) {
  console.error(`FAIL  typescript: ${failures.length} of ${total} vectors mismatched`);
  for (const f of failures) console.error("  " + f);
  process.exit(1);
}
console.log(`PASS  typescript: ${doc.vectors.length} accept + ${doc.rejects.length} reject vectors, profile ${doc.profile}`);
