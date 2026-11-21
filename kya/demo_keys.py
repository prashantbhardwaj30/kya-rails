"""DEMO KEYS ONLY. Derived from public seeds so the committed examples are reproducible.

Anyone can recompute these private keys from this file. Never use them for anything real.
A production deployment would hold issuer keys in an HSM or KMS and publish only public JWKs.
"""
from __future__ import annotations

import hashlib

from .crypto import SigningKey

ISSUER_NBFC = "did:web:kya.sahyadri-finance.example"
ISSUER_PSP = "did:web:kya.paybharat-psp.example"
ISSUER_ROGUE = "did:web:kya.trusted-agents.example"  # not on any allowlist
VERIFIER = "did:web:gateway.kya-rails.example"


def _key(label: str, kid: str) -> SigningKey:
    seed = hashlib.sha256(f"kya-rails/demo-only/{label}".encode()).digest()
    return SigningKey.from_seed(kid, seed)


def issuer_key(issuer_did: str) -> SigningKey:
    return _key(f"issuer/{issuer_did}", f"{issuer_did}#key-1")


def agent_key(agent_id: str) -> SigningKey:
    return _key(f"agent/{agent_id}", f"{agent_id}#key-1")


def verifier_key() -> SigningKey:
    return _key("verifier", f"{VERIFIER}#evidence-1")
