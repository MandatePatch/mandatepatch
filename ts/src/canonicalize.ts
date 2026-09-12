/**
 * Deterministic serialization and hash encoding for mandatepatch artifacts.
 *
 * §4.3 of Technical Disclosure Commons #11517 says only this about serialization:
 *
 *   "each binding profile MUST define the deterministic serialization and hash
 *    encoding that make the commitment byte-identical across parties"
 *
 * The disclosure deliberately fixes no serialization. This module therefore ships
 * ONE explicitly-named profile, `mandatepatch/profile/v1`, as a *choice*, and makes
 * the profile pluggable so that an AP2, Verifiable Intent, or ACP binding can
 * register its own without forking the artifact layer.
 *
 * PROFILE-DEFINED decisions taken by v1 are listed in README.md and marked inline
 * below with `PROFILE-DEFINED:`.
 */

import { createHash } from "node:crypto";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

/** Identifier of the default profile shipped by this repository. */
export const DEFAULT_PROFILE_ID = "mandatepatch/profile/v1";

/** Largest integer exactly representable as an IEEE-754 double (RFC 8785 number domain). */
const MAX_SAFE_INTEGER = 9007199254740991;

export type CanonicalizationErrorCode =
  | "E_UNSUPPORTED_TYPE"
  | "E_NON_FINITE_NUMBER"
  | "E_NON_INTEGER_NUMBER"
  | "E_INTEGER_OUT_OF_RANGE"
  | "E_LONE_SURROGATE"
  | "E_DUPLICATE_KEY_AFTER_NFC";

export class CanonicalizationError extends Error {
  readonly code: CanonicalizationErrorCode;
  readonly path: string;
  constructor(code: CanonicalizationErrorCode, path: string, message: string) {
    super(`${code} at ${path}: ${message}`);
    this.name = "CanonicalizationError";
    this.code = code;
    this.path = path;
  }
}

function fail(code: CanonicalizationErrorCode, path: string, message: string): never {
  throw new CanonicalizationError(code, path, message);
}

/**
 * Compare two strings by UTF-16 code unit, which is the ordering RFC 8785 §3.2.3
 * requires for object member names. JavaScript's native `<` on strings is already
 * UTF-16 code-unit order; it is spelled out here so the Python port can match it
 * exactly (Python compares by code point, which differs above the BMP).
 */
export function compareUtf16(a: string, b: string): number {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const ca = a.charCodeAt(i);
    const cb = b.charCodeAt(i);
    if (ca !== cb) return ca < cb ? -1 : 1;
  }
  return a.length === b.length ? 0 : a.length < b.length ? -1 : 1;
}

/**
 * PROFILE-DEFINED: Unicode form. v1 normalizes every object key and every string
 * value to NFC before serialization. NFC is canonical equivalence (e + U+0301 → é)
 * so two parties that typed the same text hash the same bytes. It does not
 * neutralize homoglyphs; that is §6.3 renderer territory (draft-schrock). Lone
 * surrogates are rejected rather than replaced.
 */
function normalizeString(value: string, path: string): string {
  for (let i = 0; i < value.length; i++) {
    const c = value.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const next = i + 1 < value.length ? value.charCodeAt(i + 1) : 0;
      if (next < 0xdc00 || next > 0xdfff) {
        fail("E_LONE_SURROGATE", path, "unpaired high surrogate");
      }
      i++;
    } else if (c >= 0xdc00 && c <= 0xdfff) {
      fail("E_LONE_SURROGATE", path, "unpaired low surrogate");
    }
  }
  return value.normalize("NFC");
}

/**
 * PROFILE-DEFINED: number domain. v1 admits integers only.
 *
 * RFC 8785 requires ECMAScript `Number::toString` for numbers, which is exact but
 * awkward to reproduce identically outside a JavaScript engine. Profile v1 sidesteps
 * the whole class of cross-language float-formatting divergence by admitting no
 * non-integer number anywhere: §4.3 monetary values are carried as integer minor
 * units, quantities as integers, tax rates as integer basis points. A future profile
 * that needs non-integer numbers MUST specify ECMAScript `Number::toString` exactly.
 */
function serializeNumber(value: number, path: string): string {
  if (!Number.isFinite(value)) fail("E_NON_FINITE_NUMBER", path, "NaN and Infinity are not JSON");
  if (!Number.isInteger(value)) {
    fail("E_NON_INTEGER_NUMBER", path, "profile v1 admits integers only; use integer minor units");
  }
  if (Math.abs(value) > MAX_SAFE_INTEGER) {
    fail("E_INTEGER_OUT_OF_RANGE", path, "outside the exactly-representable integer range");
  }
  // Normalizes -0 to "0"; String() on a safe integer never uses exponent notation.
  return String(value === 0 ? 0 : value);
}

/** RFC 8785 §3.2.2.2 string escaping (the ECMAScript JSON.stringify quote algorithm). */
function serializeString(value: string): string {
  let out = '"';
  for (let i = 0; i < value.length; i++) {
    const c = value.charCodeAt(i);
    switch (c) {
      case 0x08: out += "\\b"; break;
      case 0x09: out += "\\t"; break;
      case 0x0a: out += "\\n"; break;
      case 0x0c: out += "\\f"; break;
      case 0x0d: out += "\\r"; break;
      case 0x22: out += '\\"'; break;
      case 0x5c: out += "\\\\"; break;
      default:
        if (c < 0x20) {
          out += "\\u" + c.toString(16).padStart(4, "0");
        } else {
          out += value[i];
        }
    }
  }
  return out + '"';
}

/**
 * Validate and NFC-normalize a value tree. Returns a new tree; the input is not
 * mutated. Duplicate keys that collide only after NFC are rejected rather than
 * silently merged — a collision would otherwise let two different documents hash
 * to the same commitment.
 */
export function prepare(value: unknown, path = "$"): JsonValue {
  if (value === null) return null;
  const t = typeof value;
  if (t === "boolean") return value as boolean;
  if (t === "number") {
    serializeNumber(value as number, path); // validation only
    return (value as number) === 0 ? 0 : (value as number);
  }
  if (t === "string") return normalizeString(value as string, path);
  if (Array.isArray(value)) {
    return value.map((item, i) => prepare(item, `${path}[${i}]`));
  }
  if (t === "object") {
    const out: { [key: string]: JsonValue } = {};
    const seen = new Set<string>();
    for (const key of Object.keys(value as object)) {
      const nk = normalizeString(key, `${path}.${key}`);
      if (seen.has(nk)) {
        fail("E_DUPLICATE_KEY_AFTER_NFC", `${path}.${key}`, "two keys collide once normalized to NFC");
      }
      seen.add(nk);
      out[nk] = prepare((value as Record<string, unknown>)[key], `${path}.${nk}`);
    }
    return out;
  }
  return fail("E_UNSUPPORTED_TYPE", path, `${t} is not a JSON value`);
}

/** RFC 8785 serialization of an already-prepared tree. */
function serializePrepared(value: JsonValue, path = "$"): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return serializeNumber(value, path);
  if (typeof value === "string") return serializeString(value);
  if (Array.isArray(value)) {
    return "[" + value.map((v, i) => serializePrepared(v, `${path}[${i}]`)).join(",") + "]";
  }
  const keys = Object.keys(value).sort(compareUtf16);
  return (
    "{" +
    keys.map((k) => serializeString(k) + ":" + serializePrepared(value[k], `${path}.${k}`)).join(",") +
    "}"
  );
}

/**
 * PROFILE-DEFINED: array ordering. RFC 8785 leaves array order alone. v1 sorts
 * `line_items` — and only `line_items` — ascending by (sku, variant_id, line_id)
 * under UTF-16 code-unit ordering, so that a producer's incidental array order
 * cannot change the commitment. Every other array in the §4.3 schema is treated as
 * order-significant and preserved as given, so producers MUST emit them stably
 * (this affects `tax.components` and `substitution_policy.allowed_substitutions`).
 */
export function sortLineItems(value: JsonValue): JsonValue {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return value;
  const obj = value as { [key: string]: JsonValue };
  const items = obj["line_items"];
  if (!Array.isArray(items)) return obj;
  const keyOf = (item: JsonValue): [string, string, string] => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) return ["", "", ""];
    const rec = item as { [key: string]: JsonValue };
    const s = (k: string) => (typeof rec[k] === "string" ? (rec[k] as string) : "");
    return [s("sku"), s("variant_id"), s("line_id")];
  };
  const sorted = [...items].sort((a, b) => {
    const ka = keyOf(a);
    const kb = keyOf(b);
    for (let i = 0; i < 3; i++) {
      const c = compareUtf16(ka[i], kb[i]);
      if (c !== 0) return c;
    }
    return 0;
  });
  return { ...obj, line_items: sorted };
}

/**
 * PROFILE-DEFINED: hash function and encoding. v1 is SHA-256 over the UTF-8 bytes
 * of the canonical string, encoded base64url without padding and prefixed with the
 * algorithm name, e.g. `sha-256:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU`. The
 * prefix is there so a later profile can move algorithms without ambiguity.
 */
export function hashCanonical(canonical: string): string {
  const digest = createHash("sha256").update(Buffer.from(canonical, "utf8")).digest();
  return "sha-256:" + digest.toString("base64url");
}

export interface CanonicalizationProfile {
  readonly id: string;
  /** RFC 8785 canonical string for any JSON value. Applies no array reordering. */
  canonicalize(value: unknown): string;
  /** `sha-256:<base64url>` over the canonical string. Use for artifact hashes. */
  digest(value: unknown): string;
  /**
   * §4.3 canonical authorization transaction commitment: prepare, apply the
   * profile's line-item ordering rule, serialize, hash.
   */
  canonicalCommitment(commitment: unknown): { canonical: string; digest: string };
}

export const profileV1: CanonicalizationProfile = {
  id: DEFAULT_PROFILE_ID,
  canonicalize(value: unknown): string {
    return serializePrepared(prepare(value));
  },
  digest(value: unknown): string {
    return hashCanonical(serializePrepared(prepare(value)));
  },
  canonicalCommitment(commitment: unknown): { canonical: string; digest: string } {
    const canonical = serializePrepared(sortLineItems(prepare(commitment)));
    return { canonical, digest: hashCanonical(canonical) };
  },
};

const registry = new Map<string, CanonicalizationProfile>([[profileV1.id, profileV1]]);

/** Register an additional binding profile (§4.3: "each binding profile MUST define ..."). */
export function registerProfile(profile: CanonicalizationProfile): void {
  registry.set(profile.id, profile);
}

/** Look up a profile by identifier. Throws if the profile is not registered. */
export function getProfile(id: string = DEFAULT_PROFILE_ID): CanonicalizationProfile {
  const p = registry.get(id);
  if (!p) throw new Error(`unknown canonicalization profile: ${id}`);
  return p;
}

/** Convenience wrappers over the default profile. */
export const canonicalize = (value: unknown): string => profileV1.canonicalize(value);
export const digest = (value: unknown): string => profileV1.digest(value);
export const canonicalCommitment = (c: unknown): { canonical: string; digest: string } =>
  profileV1.canonicalCommitment(c);
