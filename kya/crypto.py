"""Ed25519 keys and compact JWS with a detached payload (RFC 7515 Appendix F, RFC 8037 EdDSA).

Signing input = BASE64URL(header) || "." || BASE64URL(canonical payload).
The payload is removed from the serialised token, giving "header..signature".
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_bytes


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private: Ed25519PrivateKey

    @property
    def public(self) -> Ed25519PublicKey:
        return self.private.public_key()

    def public_jwk(self) -> dict[str, str]:
        raw = self.public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return {"kty": "OKP", "crv": "Ed25519", "x": b64url(raw), "kid": self.kid}

    @classmethod
    def from_seed(cls, kid: str, seed: bytes) -> "SigningKey":
        if len(seed) != 32:
            raise ValueError("Ed25519 seed must be 32 bytes")
        return cls(kid=kid, private=Ed25519PrivateKey.from_private_bytes(seed))


def public_key_from_jwk(jwk: dict[str, Any]) -> Ed25519PublicKey:
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise ValueError("only OKP/Ed25519 keys are supported")
    return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))


def _strip_proof(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in obj.items() if k != "proof"}


def sign_detached(obj: dict[str, Any], key: SigningKey, typ: str) -> dict[str, str]:
    """Return a proof object for obj (any existing proof field is excluded from the payload)."""
    header = {"alg": "EdDSA", "kid": key.kid, "typ": typ}
    h = b64url(canonical_bytes(header))
    p = b64url(canonical_bytes(_strip_proof(obj)))
    sig = key.private.sign(f"{h}.{p}".encode("ascii"))
    return {"alg": "EdDSA", "kid": key.kid, "jws": f"{h}..{b64url(sig)}"}


class SignatureError(Exception):
    pass


def verify_detached(obj: dict[str, Any], public: Ed25519PublicKey, expected_typ: str) -> dict[str, Any]:
    """Verify obj['proof'] against public. Returns the protected header. Raises SignatureError."""
    proof = obj.get("proof") or {}
    token = proof.get("jws", "")
    parts = token.split(".")
    if len(parts) != 3 or parts[1] != "":
        raise SignatureError("proof.jws is not a detached compact JWS")
    try:
        header = json.loads(b64url_decode(parts[0]))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SignatureError("protected header is not valid base64url JSON") from exc
    if header.get("alg") != "EdDSA":
        raise SignatureError(f"unsupported alg {header.get('alg')!r}")
    if header.get("typ") != expected_typ:
        raise SignatureError(f"typ {header.get('typ')!r} != {expected_typ!r}")
    if header.get("kid") != proof.get("kid"):
        raise SignatureError("kid in header does not match proof.kid")
    p = b64url(canonical_bytes(_strip_proof(obj)))
    try:
        public.verify(b64url_decode(parts[2]), f"{parts[0]}.{p}".encode("ascii"))
    except InvalidSignature as exc:
        raise SignatureError("signature does not verify over the canonical payload") from exc
    return header
