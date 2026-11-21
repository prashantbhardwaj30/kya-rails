"""Gate 1: identity verification.

Answers MAS KYA item (a) "who the agent is" and SAFR's Agent Identity component: bind the
proposed action to a recognised, registered agent before any other evaluation proceeds.

Rules
  ID-001  manifest is valid against manifest.schema.json
  ID-002  action envelope is valid against action.schema.json
  ID-003  manifest issuer is on the verifier's allowlist
  ID-004  issuer may vouch for every action type the manifest grants
  ID-005  manifest signature verifies with the issuer's key (EdDSA, detached JWS)
  ID-006  manifest is inside its issued_at / expires_at window
  ID-007  manifest has not been revoked (issuer status list)
  ID-008  action names this manifest and this agent
  ID-009  action is signed by the agent key published in the manifest (proof of possession)
  ID-010  action is fresh and not a replay (unique action_id, clock skew under 5 minutes)
  ID-011  assurance tier is high enough for the action class

Run:  python -m gates.identity_gate spec/examples/valid/loan-disbursal.manifest.json spec/examples/valid/loan-disbursal.action.json
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from kya import schema
from kya.crypto import SignatureError, public_key_from_jwk, verify_detached
from kya.registry import TrustRegistry

from .base import GateResult, parse_dt

GATE = "identity"
MANIFEST_TYP = "kya-manifest+jws"
ACTION_TYP = "kya-action+jws"
MAX_SKEW = timedelta(minutes=5)
TIER_ORDER = {"T1": 1, "T2": 2, "T3": 3}
# Our policy, in the spirit of "controls proportionate to authority" (MAS keynote para 50d).
REQUIRED_TIER = {"credit_report.pull": "T2", "loan.disburse": "T2", "payment.upi_p2m": "T1",
                 "payment.reserve_debit": "T1", "payment.link_create": "T1"}


def run(manifest: dict[str, Any], action: dict[str, Any], registry: TrustRegistry, now: datetime,
        consume: bool = True) -> GateResult:
    r = GateResult(GATE)

    m_errs = schema.errors("manifest", manifest)
    r.add("ID-001", "Manifest matches KYA schema", "fail" if m_errs else "pass",
          "; ".join(m_errs[:3]) if m_errs else "manifest.schema.json (draft 2020-12), strict")
    a_errs = schema.errors("action", action)
    r.add("ID-002", "Action envelope matches schema", "fail" if a_errs else "pass",
          "; ".join(a_errs[:3]) if a_errs else "action.schema.json (draft 2020-12), strict")
    if m_errs or a_errs:
        return r  # SAFR: an envelope that fails identity is rejected immediately and logged

    issuer_did = manifest["issuer"]
    issuer = registry.issuers.get(issuer_did)
    r.add("ID-003", "Issuer is on the allowlist", "pass" if issuer else "fail",
          "trusted issuer" if issuer else "issuer is not a trusted KYA issuer for this verifier",
          observed=issuer_did, expected=sorted(registry.issuers))
    if issuer is None:
        return r

    granted = set(manifest["authority"]["permitted_actions"])
    beyond = sorted(granted - issuer.allowed_actions)
    r.add("ID-004", "Issuer may vouch for these actions", "fail" if beyond else "pass",
          f"issuer cannot grant {beyond}" if beyond else "all granted action types are within the issuer's remit",
          observed=sorted(granted), expected=sorted(issuer.allowed_actions))

    try:
        verify_detached(manifest, public_key_from_jwk(issuer.public_jwk), MANIFEST_TYP)
        if manifest["proof"]["kid"] != issuer.public_jwk["kid"]:
            raise SignatureError("manifest was signed with a key id this issuer does not publish")
        r.add("ID-005", "Issuer signature verifies", "pass", "EdDSA over canonical manifest", observed=manifest["proof"]["kid"])
    except SignatureError as exc:
        r.add("ID-005", "Issuer signature verifies", "fail", str(exc), observed=manifest["proof"]["kid"])

    issued, expires = parse_dt(manifest["issued_at"]), parse_dt(manifest["expires_at"])
    in_window = issued <= now < expires
    r.add("ID-006", "Manifest is within its validity window", "pass" if in_window else "fail",
          "valid now" if in_window else ("not yet valid" if now < issued else "manifest expired"),
          observed=now.isoformat(), expected=f"{manifest['issued_at']} .. {manifest['expires_at']}")

    idx = manifest["authority"]["revocation"]["status_list_index"]
    revoked = registry.is_revoked(issuer_did, idx)
    r.add("ID-007", "Manifest is not revoked", "fail" if revoked else "pass",
          "revoked by principal or issuer" if revoked else "status list index not revoked", observed=idx)

    binds = action["manifest_id"] == manifest["manifest_id"] and action["agent_id"] == manifest["identity"]["agent_id"]
    r.add("ID-008", "Action is bound to this manifest and agent", "pass" if binds else "fail",
          "manifest_id and agent_id match" if binds else "action names a different manifest or agent",
          observed={"manifest_id": action["manifest_id"], "agent_id": action["agent_id"]})

    try:
        verify_detached(action, public_key_from_jwk(manifest["identity"]["public_key"]), ACTION_TYP)
        if action["proof"]["kid"] != manifest["identity"]["public_key"]["kid"]:
            raise SignatureError("action kid does not match the agent key in the manifest")
        r.add("ID-009", "Agent signed the action (proof of possession)", "pass", "EdDSA with the manifest's agent key")
    except SignatureError as exc:
        r.add("ID-009", "Agent signed the action (proof of possession)", "fail", str(exc))

    skew = abs(now - parse_dt(action["requested_at"]))
    replay = action["action_id"] in registry.seen_action_ids
    fresh = skew <= MAX_SKEW and not replay
    r.add("ID-010", "Action is fresh and not replayed", "pass" if fresh else "fail",
          "unique action_id, timestamp within 5 minutes" if fresh else
          ("action_id already used" if replay else f"timestamp skew {int(skew.total_seconds())}s exceeds 300s"),
          observed=action["action_id"])
    if consume and fresh:
        registry.seen_action_ids.add(action["action_id"])

    tier = manifest["assurance"]["trust_tier"]
    need = REQUIRED_TIER[action["action_type"]]
    evals_ok = all(e["passed"] for e in manifest["assurance"]["evaluations"])
    ok = TIER_ORDER[tier] >= TIER_ORDER[need] and evals_ok
    r.add("ID-011", "Assurance is proportionate to the action", "pass" if ok else "fail",
          f"tier {tier} meets {need}" + ("" if evals_ok else ", but a declared evaluation failed")
          if TIER_ORDER[tier] >= TIER_ORDER[need] else f"tier {tier} is below {need} required for {action['action_type']}",
          observed=tier, expected=need)
    return r


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    from kya.defaults import DEMO_NOW, demo_registry

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("manifest")
    p.add_argument("action")
    p.add_argument("--now", default=DEMO_NOW.isoformat(), help="evaluation time, ISO 8601 (default: demo clock)")
    a = p.parse_args(argv)
    res = run(json.load(open(a.manifest, encoding="utf-8")), json.load(open(a.action, encoding="utf-8")),
              demo_registry(), datetime.fromisoformat(a.now))
    print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
    return 0 if res.decision != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
