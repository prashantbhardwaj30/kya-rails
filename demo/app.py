"""FastAPI demo server. Local only, no keys, no network calls.

    uvicorn demo.app:app --port 8000      then open http://127.0.0.1:8000
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse

from adapters import atom_a2a, npci_upi, whatsapp_razorpay
from gates import identity_gate
from kya import __version__
from kya.defaults import DEMO_NOW, demo_registry
from kya.demo_keys import verifier_key
from kya.evidence import EvidenceLedger
from kya.pipeline import evaluate

from .scenarios import BY_ID, ONBOARD, SCENARIOS, fresh_action, load, summary

STATIC = Path(__file__).resolve().parent / "static"
ADAPTERS = {"npci_upi": npci_upi, "whatsapp_razorpay": whatsapp_razorpay}

app = FastAPI(title="kya-rails demo", version=__version__,
              description="Know Your Agent reference implementation. All data fictional, all rails mocked.")


class State:
    def __init__(self) -> None:
        self.tick = 0
        self.registry = demo_registry()
        self.ledger = EvidenceLedger(verifier_key(), clock=self.now)
        self.runs = 0
        self.last: tuple[dict[str, Any], dict[str, Any]] | None = None
        self.onboarded = False

    def now(self) -> datetime:
        return DEMO_NOW + timedelta(seconds=self.tick)

    def advance(self, seconds: int = 7) -> datetime:
        self.tick += seconds
        return self.now()


S = State()


def _ledger_tail(n: int = 40) -> list[dict[str, Any]]:
    return S.ledger.records[-n:]


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "demo_clock": S.now().isoformat(), "records": len(S.ledger.records)}


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return [{"id": s.id, "group": s.group, "title": s.title, "subtitle": s.subtitle, "expect": s.expect,
             "caption": s.caption} for s in SCENARIOS]


def _onboard() -> dict[str, Any]:
    now = S.advance(3)
    out = []
    for rel in ONBOARD:
        m = load(rel)
        res = identity_gate.manifest_checks(m, S.registry, now)
        if res.decision != "FAIL":
            S.registry.onboard(m)
        S.ledger.append("onboarding", {"agent_id": m["identity"]["agent_id"], "manifest_id": m["manifest_id"], **res.to_dict()})
        out.append({"agent": summary(m), "gate": res.to_dict(), "registered": res.decision != "FAIL"})
    S.onboarded = True
    return {"scenario": "onboard", "onboarded": out, "ledger": _ledger_tail(), "demo_clock": now.isoformat()}


@app.post("/api/run/{scenario_id}")
def run(scenario_id: str) -> dict[str, Any]:
    s = BY_ID.get(scenario_id)
    if s is None:
        raise HTTPException(404, f"unknown scenario {scenario_id}")
    if s.id == "onboard":
        return _onboard()
    if not S.onboarded:
        _onboard()
    S.runs += 1
    now = S.advance()
    manifest = load(s.manifest)
    action = fresh_action(s, S.runs, now.isoformat())
    return _evaluate(manifest, action, now, s.id, s.adapter)


def _evaluate(manifest: dict[str, Any], action: dict[str, Any], now: datetime, sid: str, adapter: str | None) -> dict[str, Any]:
    result = evaluate(manifest, action, S.registry, S.ledger, now)
    S.last = (copy.deepcopy(manifest), copy.deepcopy(action))
    rail = ADAPTERS[adapter].build_request(manifest, action, result, now) if adapter else None
    return {
        "scenario": sid,
        "agent": summary(manifest),
        "instruction": action["instruction"],
        "proposed": {"action_type": action["action_type"], **action["params"]},
        "trace": action["trace"],
        "result": result,
        "rail": rail,
        "a2a_evidence": atom_a2a.wrap(S.ledger.records[-1], "did:web:verifier.sahyadri-finance.example", "did:web:network.example"),
        "ledger": _ledger_tail(),
        "demo_clock": now.isoformat(),
    }


@app.post("/api/replay")
def replay() -> dict[str, Any]:
    """Resubmit the last envelope unchanged: ID-010 must catch it."""
    if S.last is None:
        raise HTTPException(409, "run a scenario first")
    manifest, action = S.last
    return _evaluate(manifest, action, S.advance(2), "replay", None)


@app.post("/api/evaluate")
def evaluate_custom(payload: dict[str, Any] = Body(..., examples=[{"manifest": {}, "action": {}}])) -> dict[str, Any]:
    """Evaluate your own manifest and action against the demo trust registry."""
    if not isinstance(payload.get("manifest"), dict) or not isinstance(payload.get("action"), dict):
        raise HTTPException(422, "body must be {'manifest': {...}, 'action': {...}}")
    now = S.advance()
    return evaluate(payload["manifest"], payload["action"], S.registry, S.ledger, now)


@app.get("/api/ledger")
def ledger() -> dict[str, Any]:
    return {"records": S.ledger.records, "head": S.ledger.head}


@app.get("/api/ledger/verify")
def verify() -> dict[str, Any]:
    return S.ledger.verify()


@app.post("/api/ledger/tamper")
def tamper() -> dict[str, Any]:
    """Simulate an insider editing the log to hide a DENY. Verification must then fail."""
    for rec in S.ledger.records:  # earliest DENY, so every later record becomes unprovable too
        if rec["kind"] == "disposition" and rec["body"]["outcome"] == "DENY":
            rec["body"]["outcome"] = "AUTO_EXECUTE"
            return {"tampered_seq": rec["seq"], "change": "outcome DENY -> AUTO_EXECUTE", "verify": S.ledger.verify()}
    for rec in reversed(S.ledger.records):
        if rec["kind"] == "disposition":
            rec["body"]["outcome"] = "DENY"
            return {"tampered_seq": rec["seq"], "change": "outcome -> DENY", "verify": S.ledger.verify()}
    raise HTTPException(409, "nothing to tamper with yet")


@app.post("/api/reset")
def reset() -> dict[str, Any]:
    global S
    S = State()
    return {"ok": True, "demo_clock": S.now().isoformat()}
