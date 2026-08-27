"""Deterministic serialization and hash encoding for mandatepatch artifacts.

Section 4.3 of Technical Disclosure Commons #11517 says only this about
serialization:

    "each binding profile MUST define the deterministic serialization and hash
     encoding that make the commitment byte-identical across parties"

The disclosure deliberately fixes no serialization. This module therefore ships
ONE explicitly-named profile, ``mandatepatch/profile/v1``, as a *choice*, and
makes the profile pluggable so that an AP2, Verifiable Intent, or ACP binding can
register its own without forking the artifact layer.

This file is a line-for-line port of ``ts/src/canonicalize.ts``. The two are
required to produce byte-identical output; ``examples/canonicalization-vectors.json``
is the shared test vector file that both CI jobs check against.

PROFILE-DEFINED decisions taken by v1 are listed in README.md and marked inline
below with ``PROFILE-DEFINED:``.
"""

from __future__ import annotations

import base64
import hashlib
import unicodedata
from typing import Any, Callable, Dict, List, Tuple

__all__ = [
    "DEFAULT_PROFILE_ID",
    "CanonicalizationError",
    "CanonicalizationProfile",
    "canonicalize",
    "canonical_commitment",
    "compare_utf16",
    "digest",
    "get_profile",
    "hash_canonical",
    "prepare",
    "profile_v1",
    "register_profile",
    "sort_line_items",
]

#: Identifier of the default profile shipped by this repository.
DEFAULT_PROFILE_ID = "mandatepatch/profile/v1"

#: Largest integer exactly representable as an IEEE-754 double (RFC 8785 number domain).
MAX_SAFE_INTEGER = 9007199254740991


class CanonicalizationError(ValueError):
    """Raised when a value falls outside profile v1's admitted value space."""

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(f"{code} at {path}: {message}")
        self.code = code
        self.path = path


def _fail(code: str, path: str, message: str) -> None:
    raise CanonicalizationError(code, path, message)


def _utf16_key(value: str) -> bytes:
    """UTF-16 code-unit sort key.

    RFC 8785 section 3.2.3 orders object member names by UTF-16 code unit.
    Python compares strings by code point, which differs above the BMP (U+10000
    sorts *before* U+FFFF in UTF-16 order and *after* it by code point), so the
    comparison is done on big-endian UTF-16 bytes instead.
    """
    return value.encode("utf-16-be", "surrogatepass")


def compare_utf16(a: str, b: str) -> int:
    """Compare two strings by UTF-16 code unit. Mirrors ``compareUtf16`` in the TS port."""
    ka, kb = _utf16_key(a), _utf16_key(b)
    if ka < kb:
        return -1
    if ka > kb:
        return 1
    return 0


def _normalize_string(value: str, path: str) -> str:
    """PROFILE-DEFINED: Unicode form.

    v1 normalizes every object key and every string value to NFC before
    serialization. Section 8 lists "homoglyphs" and "locale separator confusion"
    among the display attacks "the canonicalization profile answers"; NFC is the
    minimum needed for two parties that typed the same text to hash the same
    bytes. Lone surrogates are rejected rather than replaced.
    """
    for ch in value:
        if 0xD800 <= ord(ch) <= 0xDFFF:
            _fail("E_LONE_SURROGATE", path, "unpaired surrogate")
    return unicodedata.normalize("NFC", value)


def _serialize_number(value: Any, path: str) -> str:
    """PROFILE-DEFINED: number domain. v1 admits integers only.

    RFC 8785 requires ECMAScript ``Number::toString`` for numbers, which is exact
    but awkward to reproduce identically outside a JavaScript engine. Profile v1
    sidesteps the whole class of cross-language float-formatting divergence by
    admitting no non-integer number anywhere: section 4.3 monetary values are
    carried as integer minor units, quantities as integers, tax rates as integer
    basis points. A future profile that needs non-integer numbers MUST specify
    ECMAScript ``Number::toString`` exactly.
    """
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            _fail("E_NON_FINITE_NUMBER", path, "NaN and Infinity are not JSON")
        if not value.is_integer():
            _fail(
                "E_NON_INTEGER_NUMBER",
                path,
                "profile v1 admits integers only; use integer minor units",
            )
        value = int(value)
    if abs(value) > MAX_SAFE_INTEGER:
        _fail("E_INTEGER_OUT_OF_RANGE", path, "outside the exactly-representable integer range")
    # Normalizes -0 to "0"; str() on a Python int never uses exponent notation.
    return str(int(value) + 0)


_ESCAPES = {
    0x08: "\\b",
    0x09: "\\t",
    0x0A: "\\n",
    0x0C: "\\f",
    0x0D: "\\r",
    0x22: '\\"',
    0x5C: "\\\\",
}


def _serialize_string(value: str) -> str:
    """RFC 8785 section 3.2.2.2 string escaping (the ECMAScript JSON.stringify quote algorithm)."""
    out: List[str] = ['"']
    for ch in value:
        code = ord(ch)
        esc = _ESCAPES.get(code)
        if esc is not None:
            out.append(esc)
        elif code < 0x20:
            out.append("\\u%04x" % code)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def prepare(value: Any, path: str = "$") -> Any:
    """Validate and NFC-normalize a value tree.

    Returns a new tree; the input is not mutated. Duplicate keys that collide only
    after NFC are rejected rather than silently merged - a collision would
    otherwise let two different documents hash to the same commitment.
    """
    if value is None:
        return None
    if isinstance(value, bool):  # must precede the int check: bool subclasses int
        return value
    if isinstance(value, (int, float)):
        _serialize_number(value, path)  # validation only
        return int(value)
    if isinstance(value, str):
        return _normalize_string(value, path)
    if isinstance(value, (list, tuple)):
        return [prepare(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        seen = set()
        for key in value:
            if not isinstance(key, str):
                _fail("E_UNSUPPORTED_TYPE", path, "object keys must be strings")
            nk = _normalize_string(key, f"{path}.{key}")
            if nk in seen:
                _fail(
                    "E_DUPLICATE_KEY_AFTER_NFC",
                    f"{path}.{key}",
                    "two keys collide once normalized to NFC",
                )
            seen.add(nk)
            out[nk] = prepare(value[key], f"{path}.{nk}")
        return out
    _fail("E_UNSUPPORTED_TYPE", path, f"{type(value).__name__} is not a JSON value")
    raise AssertionError("unreachable")


def _serialize_prepared(value: Any, path: str = "$") -> str:
    """RFC 8785 serialization of an already-prepared tree."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _serialize_number(value, path)
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize_prepared(v, f"{path}[{i}]") for i, v in enumerate(value)) + "]"
    keys = sorted(value.keys(), key=_utf16_key)
    return (
        "{"
        + ",".join(
            _serialize_string(k) + ":" + _serialize_prepared(value[k], f"{path}.{k}") for k in keys
        )
        + "}"
    )


def sort_line_items(value: Any) -> Any:
    """PROFILE-DEFINED: array ordering.

    RFC 8785 leaves array order alone. v1 sorts ``line_items`` - and only
    ``line_items`` - ascending by (sku, variant_id, line_id) under UTF-16
    code-unit ordering, so that a producer's incidental array order cannot change
    the commitment. Every other array in the section 4.3 schema is treated as
    order-significant and preserved as given, so producers MUST emit them stably
    (this affects ``tax.components`` and ``substitution_policy.allowed_substitutions``).
    """
    if not isinstance(value, dict):
        return value
    items = value.get("line_items")
    if not isinstance(items, list):
        return value

    def key_of(item: Any) -> Tuple[bytes, bytes, bytes]:
        if not isinstance(item, dict):
            return (b"", b"", b"")
        def s(k: str) -> bytes:
            v = item.get(k)
            return _utf16_key(v) if isinstance(v, str) else b""
        return (s("sku"), s("variant_id"), s("line_id"))

    out = dict(value)
    out["line_items"] = sorted(items, key=key_of)
    return out


def hash_canonical(canonical: str) -> str:
    """PROFILE-DEFINED: hash function and encoding.

    v1 is SHA-256 over the UTF-8 bytes of the canonical string, encoded base64url
    without padding and prefixed with the algorithm name, e.g.
    ``sha-256:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU``. The prefix is there so
    a later profile can move algorithms without ambiguity.
    """
    raw = hashlib.sha256(canonical.encode("utf-8")).digest()
    return "sha-256:" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class CanonicalizationProfile:
    """A named deterministic serialization + hash encoding (section 4.3)."""

    def __init__(
        self,
        profile_id: str,
        canonicalize_fn: Callable[[Any], str],
        commitment_fn: Callable[[Any], Dict[str, str]],
    ) -> None:
        self.id = profile_id
        self._canonicalize = canonicalize_fn
        self._commitment = commitment_fn

    def canonicalize(self, value: Any) -> str:
        """RFC 8785 canonical string for any JSON value. Applies no array reordering."""
        return self._canonicalize(value)

    def digest(self, value: Any) -> str:
        """``sha-256:<base64url>`` over the canonical string. Use for artifact hashes."""
        return hash_canonical(self._canonicalize(value))

    def canonical_commitment(self, commitment: Any) -> Dict[str, str]:
        """Section 4.3 commitment: prepare, apply the line-item ordering rule, serialize, hash."""
        return self._commitment(commitment)


def _v1_canonicalize(value: Any) -> str:
    return _serialize_prepared(prepare(value))


def _v1_commitment(commitment: Any) -> Dict[str, str]:
    canonical = _serialize_prepared(sort_line_items(prepare(commitment)))
    return {"canonical": canonical, "digest": hash_canonical(canonical)}


profile_v1 = CanonicalizationProfile(DEFAULT_PROFILE_ID, _v1_canonicalize, _v1_commitment)

_REGISTRY: Dict[str, CanonicalizationProfile] = {profile_v1.id: profile_v1}


def register_profile(profile: CanonicalizationProfile) -> None:
    """Register an additional binding profile (4.3: 'each binding profile MUST define ...')."""
    _REGISTRY[profile.id] = profile


def get_profile(profile_id: str = DEFAULT_PROFILE_ID) -> CanonicalizationProfile:
    """Look up a profile by identifier. Raises if the profile is not registered."""
    try:
        return _REGISTRY[profile_id]
    except KeyError:
        raise KeyError(f"unknown canonicalization profile: {profile_id}") from None


def canonicalize(value: Any) -> str:
    """Convenience wrapper over the default profile."""
    return profile_v1.canonicalize(value)


def digest(value: Any) -> str:
    """Convenience wrapper over the default profile."""
    return profile_v1.digest(value)


def canonical_commitment(commitment: Any) -> Dict[str, str]:
    """Convenience wrapper over the default profile."""
    return profile_v1.canonical_commitment(commitment)
