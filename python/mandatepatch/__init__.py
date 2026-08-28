"""mandatepatch - reference implementation of the artifact layer described in
Technical Disclosure Commons #11517, "Mandate Lifecycle Extensions for Agentic
Payment Credentials" (Matt Kirby, CC-BY).

The artifact layer ships first. This package defines the objects and their
canonical form. It deliberately implements no semantic scorer, no service, and no
policy engine.
"""

from .canonicalize import (
    DEFAULT_PROFILE_ID,
    CanonicalizationError,
    CanonicalizationProfile,
    canonical_commitment,
    canonicalize,
    compare_utf16,
    digest,
    get_profile,
    hash_canonical,
    prepare,
    profile_v1,
    register_profile,
    sort_line_items,
)

__version__ = "0.1.4"

__all__ = [
    "DEFAULT_PROFILE_ID",
    "CanonicalizationError",
    "CanonicalizationProfile",
    "__version__",
    "canonical_commitment",
    "canonicalize",
    "compare_utf16",
    "digest",
    "get_profile",
    "hash_canonical",
    "prepare",
    "profile_v1",
    "register_profile",
    "sort_line_items",
]
