"""Gate 2: authority and mandate check.

Answers MAS KYA items (b) "what authority it has been given" and (c) "what mandate it
operates under". Implements SAFR's point that an agent cannot extend a mandate through its
own reasoning: every rule here is a deterministic comparison, no model is consulted.

Rules
  MD-001  action type is granted by the authority section
  MD-002  delegation depth does not exceed the permitted depth
  MD-003  mandate is inside its validity window
  MD-004  action purpose is one of the mandate's purposes
  MD-005  amount is within the per-transaction cap
  MD-006  amount plus spend so far is within the aggregate cap
  MD-007  merchant category (MCC) is allowed
  MD-008  payee is on the mandate's payee allowlist (if the mandate has one)
  MD-009  DPDP consent is active (not withdrawn, not expired)
  MD-010  DPDP purpose limitation: action purpose is a consented purpose
  MD-011  DPDP data minimisation: requested data categories are all consented
  MD-012  amount above the human-approval threshold is escalated, not executed

MD-009 to MD-011 model the Digital Personal Data Protection Act, 2023, s.6 (consent limited
to the specified purpose and the data necessary for it). They are an engineering control,
not legal advice.

Run:  python -m gates.mandate_gate spec/examples/attacks/purpose-misuse.action.json --manifest spec/examples/valid/credit-bureau-check.manifest.json
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from kya.registry import TrustRegistry

from .base import GateResult, parse_dt, rupees

GATE = "mandate"
MONEY_ACTIONS = {"loan.disburse", "payment.upi_p2m", "payment.reserve_debit", "payment.link_create"}


def run(manifest: dict[str, Any], action: dict[str, Any], registry: TrustRegistry, now: datetime) -> GateResult:
    r = GateResult(GATE)
    auth, mdt = manifest["authority"], manifest["mandate"]
    params, limits, consent = action["params"], mdt["limits"], mdt["consent"]
    atype, amount, purpose = action["action_type"], params["amount_paise"], params["purpose"]

    granted = atype in auth["permitted_actions"]
    r.add("MD-001", "Action type is authorised", "pass" if granted else "fail",
          f"{atype} is granted" if granted else f"{atype} is not in permitted_actions",
          observed=atype, expected=auth["permitted_actions"])

    d = auth["delegation"]
    r.add("MD-002", "Delegation depth within limit", "pass" if d["depth"] <= d["max_depth"] else "fail",
          f"depth {d['depth']} of max {d['max_depth']}", observed=d["depth"], expected=d["max_depth"])

    start, end = parse_dt(mdt["valid_from"]), parse_dt(mdt["valid_until"])
    live = start <= now < end
    r.add("MD-003", "Mandate is in force", "pass" if live else "fail",
          "inside validity window" if live else "outside validity window",
          observed=now.isoformat(), expected=f"{mdt['valid_from']} .. {mdt['valid_until']}")

    ok = purpose in mdt["purpose"]
    r.add("MD-004", "Purpose matches the mandate", "pass" if ok else "fail",
          f"'{purpose}' is a mandated purpose" if ok else f"'{purpose}' is outside the mandate",
          observed=purpose, expected=mdt["purpose"])

    cap = limits["per_txn_max_paise"]
    r.add("MD-005", "Within per-transaction cap", "pass" if amount <= cap else "fail",
          f"{rupees(amount)} vs cap {rupees(cap)}", observed=amount, expected=f"<= {cap}")

    agent_id = manifest["identity"]["agent_id"]
    spent = registry.spent_since(agent_id, start)
    agg = limits["aggregate_max_paise"]
    r.add("MD-006", "Within aggregate cap", "pass" if spent + amount <= agg else "fail",
          f"{rupees(spent)} spent + {rupees(amount)} vs cap {rupees(agg)}",
          observed=spent + amount, expected=f"<= {agg}")

    mccs, mcc = mdt["allowed_merchant_categories"], params.get("merchant_category")
    if atype in MONEY_ACTIONS and mccs:
        ok = mcc in mccs
        r.add("MD-007", "Merchant category allowed", "pass" if ok else "fail",
              f"MCC {mcc} allowed" if ok else f"MCC {mcc} not in allowlist", observed=mcc, expected=mccs)
    else:
        r.add("MD-007", "Merchant category allowed", "skip", "no MCC restriction applies to this action")

    payees, payee = mdt["allowed_payees"], params.get("payee")
    if atype in MONEY_ACTIONS and payees:
        allowed = {(p["type"], p["value"]) for p in payees}
        ok = payee is not None and (payee["type"], payee["value"]) in allowed
        r.add("MD-008", "Payee is on the mandate allowlist", "pass" if ok else "fail",
              "payee allowlisted" if ok else "payee is not one the principal approved",
              observed=payee["value"] if payee else None, expected=[p["value"] for p in payees])
    else:
        r.add("MD-008", "Payee is on the mandate allowlist", "skip", "mandate has no payee allowlist")

    expired = now >= parse_dt(consent["expires_at"])
    active = not consent["withdrawn"] and not expired
    r.add("MD-009", "DPDP consent is active", "pass" if active else "fail",
          "consent active" if active else ("consent withdrawn" if consent["withdrawn"] else "consent expired"),
          observed=consent["consent_id"])

    ok = purpose in consent["purposes"]
    r.add("MD-010", "DPDP purpose limitation", "pass" if ok else "fail",
          f"'{purpose}' is a consented purpose" if ok else
          f"data consented for {consent['purposes']} cannot be used for '{purpose}' (DPDP Act s.6)",
          observed=purpose, expected=consent["purposes"])

    asked = set(params.get("data_categories", []))
    extra = sorted(asked - set(consent["data_categories"]))
    r.add("MD-011", "DPDP data minimisation", "fail" if extra else ("pass" if asked else "skip"),
          f"requests unconsented data: {extra}" if extra else
          ("all requested data categories are consented" if asked else "no personal data requested"),
          observed=sorted(asked), expected=consent["data_categories"])

    hitl = limits["human_approval_above_paise"]
    needs = atype in MONEY_ACTIONS and amount > hitl
    r.add("MD-012", "Human approval threshold", "review" if needs else "pass",
          f"{rupees(amount)} is above {rupees(hitl)}: hold for a human approver" if needs else
          f"{rupees(amount)} is within autonomous limit {rupees(hitl)}",
          observed=amount, expected=f"<= {hitl} for autonomous execution")
    return r


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    from kya.defaults import DEMO_NOW, demo_registry

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("action")
    p.add_argument("--manifest", required=True)
    p.add_argument("--now", default=DEMO_NOW.isoformat())
    a = p.parse_args(argv)
    res = run(json.load(open(a.manifest, encoding="utf-8")), json.load(open(a.action, encoding="utf-8")),
              demo_registry(), datetime.fromisoformat(a.now))
    print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
    return 0 if res.decision != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
