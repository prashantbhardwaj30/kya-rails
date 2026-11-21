"""End-to-end evaluation: identity -> mandate -> risk -> SAFR disposition -> evidence.

Follows the SAFR action lifecycle: an envelope that fails identity is rejected immediately
and the failure logged; otherwise the controls are evaluated, one of four outcomes is
returned, and the full trace is written to the tamper-evident log.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from gates import identity_gate, mandate_gate, risk_gate
from gates.base import GateResult

from .canonical import digest
from .disposition import AUTO_EXECUTE, OBSERVE, dispose
from .evidence import EvidenceLedger
from .registry import TrustRegistry, Txn


def evaluate(manifest: dict[str, Any], action: dict[str, Any], registry: TrustRegistry,
             ledger: EvidenceLedger, now: datetime) -> dict[str, Any]:
    results: list[GateResult] = []
    timings: dict[str, int] = {}
    action_id = action.get("action_id", "unknown")
    envelope_digest = digest(action)

    for name, gate in (("identity", identity_gate), ("mandate", mandate_gate), ("risk", risk_gate)):
        t0 = time.perf_counter()
        res = gate.run(manifest, action, registry, now)
        timings[name] = int((time.perf_counter() - t0) * 1_000_000)
        results.append(res)
        ledger.append("gate_result", {"action_id": action_id, "envelope_digest": envelope_digest,
                                      "elapsed_us": timings[name], **res.to_dict()})
        if name == "identity" and res.decision == "FAIL":
            break  # do not evaluate a mandate whose issuer or signature cannot be trusted

    outcome = dispose(results)
    basis = sorted({c.rule_id for r in results for c in r.checks if c.outcome in ("fail", "review", "observe")})
    decision = ledger.append("disposition", {
        "action_id": action_id,
        "agent_id": action.get("agent_id"),
        "manifest_id": manifest.get("manifest_id"),
        "mandate_id": (manifest.get("mandate") or {}).get("mandate_id"),
        "envelope_digest": envelope_digest,
        "manifest_digest": digest(manifest),
        "outcome": outcome,
        "basis_rules": basis,
        "gates_run": [r.gate for r in results],
    })

    if outcome in (AUTO_EXECUTE, OBSERVE):
        p = action["params"]
        registry.record_txn(action["agent_id"], Txn(now, p["amount_paise"], (p.get("payee") or {}).get("value"), p["purpose"]))

    return {
        "action_id": action_id,
        "outcome": outcome,
        "basis_rules": basis,
        "gates": [r.to_dict() for r in results],
        "timings_us": timings,
        "evidence_seq": decision["seq"],
        "evidence_hash": decision["hash"],
    }
