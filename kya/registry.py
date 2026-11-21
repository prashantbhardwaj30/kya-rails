"""Trust state the verifier holds: issuer allowlist, revocation status, replay cache,
onboarded manifests, and per-agent transaction history for the risk gate."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .canonical import digest


@dataclass
class TrustedIssuer:
    did: str
    public_jwk: dict[str, str]
    # Highest-impact action types this issuer may vouch for. A PSP-run registry should not
    # be able to mint loan-disbursal authority, for example.
    allowed_actions: frozenset[str]


@dataclass
class Txn:
    at: datetime
    amount_paise: int
    payee: str | None
    purpose: str


@dataclass
class TrustRegistry:
    issuers: dict[str, TrustedIssuer] = field(default_factory=dict)
    revoked: set[tuple[str, int]] = field(default_factory=set)  # (issuer, status_list_index)
    seen_action_ids: set[str] = field(default_factory=set)
    onboarded: dict[str, str] = field(default_factory=dict)  # agent_id -> manifest digest at onboarding
    history: dict[str, list[Txn]] = field(default_factory=dict)

    def allow_issuer(self, did: str, public_jwk: dict[str, str], allowed_actions: list[str]) -> None:
        self.issuers[did] = TrustedIssuer(did, public_jwk, frozenset(allowed_actions))

    def revoke(self, issuer: str, index: int) -> None:
        self.revoked.add((issuer, index))

    def is_revoked(self, issuer: str, index: int) -> bool:
        return (issuer, index) in self.revoked

    def onboard(self, manifest: dict[str, Any]) -> str:
        d = digest(manifest)
        self.onboarded[manifest["identity"]["agent_id"]] = d
        return d

    def record_txn(self, agent_id: str, txn: Txn) -> None:
        self.history.setdefault(agent_id, []).append(txn)

    def txns(self, agent_id: str, since: datetime | None = None) -> list[Txn]:
        items = self.history.get(agent_id, [])
        return [t for t in items if since is None or t.at >= since]

    def spent_since(self, agent_id: str, since: datetime) -> int:
        return sum(t.amount_paise for t in self.txns(agent_id, since))

    def window(self, agent_id: str, now: datetime, hours: int) -> list[Txn]:
        return self.txns(agent_id, now - timedelta(hours=hours))
