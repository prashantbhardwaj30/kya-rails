"""MOCK adapter: KYA evidence -> AtOM-style signed A2A JSON-RPC 2.0 message.

NPCI describes AtOM as an agent-to-agent change-orchestration platform for UPI whose wire
contract is JSON-RPC 2.0 over Google's A2A protocol, with a JWT scheme and an HMAC signer,
producing "machine readable, digitally signed interactions" for audit. That makes it a
natural carrier for KYA certification evidence between a partner bank and the network.

This module only shows the mapping: it wraps a disposition record as a JSON-RPC request and
signs it with HMAC-SHA256 over canonical JSON. Method name and params are ours, not AtOM's.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

from kya.canonical import canonical_bytes

DEMO_SHARED_SECRET = b"kya-rails-demo-only-shared-secret"  # demo only; real secrets live in a vault


def wrap(evidence_record: dict[str, Any], sender: str, receiver: str, secret: bytes = DEMO_SHARED_SECRET) -> dict[str, Any]:
    msg = {
        "jsonrpc": "2.0",
        "id": f"kya-{evidence_record['seq']}",
        "method": "kya/evidence.submit",
        "params": {
            "sender": sender,
            "receiver": receiver,
            "record": {k: evidence_record[k] for k in ("seq", "ts", "kind", "body_digest", "prev_hash", "hash", "sig")},
            "summary": {k: evidence_record["body"].get(k) for k in ("action_id", "outcome", "basis_rules", "mandate_id")},
        },
    }
    msg["signature"] = {"alg": "HS256", "value": hmac.new(secret, canonical_bytes(msg), hashlib.sha256).hexdigest()}
    return msg


def verify(msg: dict[str, Any], secret: bytes = DEMO_SHARED_SECRET) -> bool:
    body = {k: v for k, v in msg.items() if k != "signature"}
    expected = hmac.new(secret, canonical_bytes(body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, msg.get("signature", {}).get("value", ""))
