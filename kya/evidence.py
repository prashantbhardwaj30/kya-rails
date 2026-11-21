"""Tamper-evident evidence ledger.

Each record carries the hash of the previous record (a hash chain) and an Ed25519 signature
by the verifier over its own hash. Changing, deleting or reordering any record breaks
verification from that point on. This is the SAFR "Audit Log": append-only, tamper-evident,
recording the envelope, the mandate, the outcome and the specific rules applied.

The ledger is in memory here. A deployment would write the same records to WORM storage or
an append-only table and anchor the head hash externally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import canonical_bytes, digest, sha256_hex
from .crypto import SigningKey, b64url, b64url_decode

GENESIS = "0" * 64


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EvidenceLedger:
    signer: SigningKey
    clock: Callable[[], datetime] = _utc_now
    records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def head(self) -> str:
        return self.records[-1]["hash"] if self.records else GENESIS

    def append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        record = {
            "seq": len(self.records) + 1,
            "ts": self.clock().isoformat(timespec="milliseconds"),
            "kind": kind,
            "body": body,
            "body_digest": digest(body),
            "prev_hash": self.head,
            "signer_kid": self.signer.kid,
        }
        record["hash"] = sha256_hex(canonical_bytes(record))
        record["sig"] = b64url(self.signer.private.sign(bytes.fromhex(record["hash"])))
        self.records.append(record)
        return record

    def verify(self, public: Ed25519PublicKey | None = None) -> dict[str, Any]:
        """Recompute every hash, link and signature. Returns {'ok', 'checked', 'broken_at', 'reason'}."""
        public = public or self.signer.public
        prev = GENESIS
        for rec in self.records:
            unsigned = {k: v for k, v in rec.items() if k not in ("hash", "sig")}
            if rec["prev_hash"] != prev:
                return {"ok": False, "checked": rec["seq"], "broken_at": rec["seq"], "reason": "prev_hash does not match previous record"}
            if digest(rec["body"]) != rec["body_digest"]:
                return {"ok": False, "checked": rec["seq"], "broken_at": rec["seq"], "reason": "body was modified after it was recorded"}
            if sha256_hex(canonical_bytes(unsigned)) != rec["hash"]:
                return {"ok": False, "checked": rec["seq"], "broken_at": rec["seq"], "reason": "record hash mismatch"}
            try:
                public.verify(b64url_decode(rec["sig"]), bytes.fromhex(rec["hash"]))
            except InvalidSignature:
                return {"ok": False, "checked": rec["seq"], "broken_at": rec["seq"], "reason": "verifier signature invalid"}
            prev = rec["hash"]
        return {"ok": True, "checked": len(self.records), "broken_at": None, "reason": "chain intact", "head": prev}
