"""Canonical JSON used for hashing and signing.

The project only ever serialises strings, booleans, null, integers, arrays and objects
(money is integer paise, never floats). For that subset, sorted keys plus compact
separators plus UTF-8 gives the same bytes as RFC 8785 (JCS). Floats are rejected so the
subset stays honest.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise ValueError("floats are not allowed in signed KYA objects; use integer paise")
    if isinstance(value, dict):
        for v in value.values():
            _reject_floats(v)
    elif isinstance(value, list):
        for v in value:
            _reject_floats(v)


def canonical_bytes(obj: Any) -> bytes:
    _reject_floats(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    """sha256:<hex> of the canonical form of obj."""
    return "sha256:" + sha256_hex(canonical_bytes(obj))
