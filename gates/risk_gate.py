"""Gate 3: transaction risk.

A signed, in-mandate action can still be wrong: the agent may have been steered by text it
read, or may be looping. This gate looks at behaviour and provenance, not credentials.

Rules
  RK-001  velocity: transactions in the last 24h against the mandate's daily limit
  RK-002  burst: three or more actions in ten minutes (runaway agent, SAFR "Rate Limits")
  RK-003  amount anomaly: robust z-score against this agent's own history
  RK-004  new payee: first payment to this payee by this agent
  RK-005  mandate drift: manifest differs from the one approved at onboarding
  RK-006  instruction mismatch: amount differs from what the principal actually asked for
  RK-007  untrusted-content taint: payee or amount came from a document or web page, not the principal
  RK-008  injection markers: instruction-like text inside untrusted content

Design choice: anomaly signals (RK-003, RK-004) never deny on their own. Agents look
statistically unusual by design (they act at odd hours and react instantly), so these rules
escalate or observe. Provenance failures (RK-006, RK-007) deny, because they show the action
does not come from the principal. All heuristics are deterministic and listed in this file.

Run:  python -m gates.risk_gate spec/examples/attacks/injected-payee.action.json --manifest spec/examples/valid/loan-disbursal.manifest.json
"""
from __future__ import annotations

import re
import statistics
from datetime import datetime, timedelta
from typing import Any

from kya.canonical import digest
from kya.registry import TrustRegistry

from .base import GateResult, rupees

GATE = "risk"
MONEY_ACTIONS = {"loan.disburse", "payment.upi_p2m", "payment.reserve_debit", "payment.link_create"}

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above|earlier) (instructions|rules)",
    r"disregard (the )?(previous|prior|above|system)",
    r"system (note|prompt|message|override) (to|for) (the )?(ai|agent|assistant)",
    r"you are now",
    r"do not (tell|notify|inform|alert) (the )?(user|borrower|customer|principal)",
    r"(new|updated) (policy|instruction)s?:",
    r"override (the )?(mandate|limit|policy)",
]
_INJ = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
_UNIT = {"lakh": 100000, "lakhs": 100000, "lac": 100000, "crore": 10000000, "cr": 10000000, "k": 1000}
_MARKED = re.compile(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakhs?|lac|crore|cr|k)?\b"
                     r"|([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakhs?|lac|crore|cr)\b", re.IGNORECASE)
_LOOSE = re.compile(r"(?<![\w-])([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]{4,})(?![\w-])")


def _to_paise(num: str, unit: str | None) -> int:
    value = float(num.replace(",", ""))
    return int(round(value * _UNIT.get((unit or "").lower(), 1) * 100))


def stated_amounts(text: str) -> set[int]:
    """Amounts the principal explicitly stated, with a currency marker or a lakh/crore unit."""
    out = set()
    for m in _MARKED.finditer(text):
        if m.group(1):
            out.add(_to_paise(m.group(1), m.group(2)))
        else:
            out.add(_to_paise(m.group(3), m.group(4)))
    return out


def loose_amounts(text: str) -> set[int]:
    """Any grouped or 4+ digit number, used only to detect taint from untrusted content."""
    return stated_amounts(text) | {_to_paise(m.group(1), None) for m in _LOOSE.finditer(text)}


def run(manifest: dict[str, Any], action: dict[str, Any], registry: TrustRegistry, now: datetime) -> GateResult:
    r = GateResult(GATE)
    agent_id = manifest["identity"]["agent_id"]
    params, limits = action["params"], manifest["mandate"]["limits"]
    amount, atype = params["amount_paise"], action["action_type"]
    payee = (params.get("payee") or {}).get("value")
    is_money = atype in MONEY_ACTIONS

    day = registry.window(agent_id, now, 24)
    n, cap = len(day) + 1, limits["max_txn_per_day"]
    outcome = "fail" if n > cap else ("observe" if n > 0.8 * cap else "pass")
    r.add("RK-001", "Daily velocity", outcome, f"{n} actions in 24h vs limit {cap}", observed=n, expected=f"<= {cap}")

    burst = [t for t in day if t.at >= now - timedelta(minutes=10)]
    r.add("RK-002", "Burst detection", "review" if len(burst) >= 2 else "pass",
          f"{len(burst) + 1} actions in 10 minutes" + (": possible runaway loop" if len(burst) >= 2 else ""),
          observed=len(burst) + 1, expected="< 3 in 10 min")

    hist = [t.amount_paise for t in registry.txns(agent_id) if t.amount_paise > 0]
    if is_money and amount > 0 and len(hist) >= 5:
        med = statistics.median(hist)
        mad = statistics.median([abs(h - med) for h in hist]) or max(1, med * 0.05)
        z = (amount - med) / (1.4826 * mad)
        outcome = "review" if z > 6 else ("observe" if z > 3.5 else "pass")
        r.add("RK-003", "Amount anomaly (robust z-score)", outcome,
              f"z = {z:.1f} against median {rupees(int(med))} over {len(hist)} past transactions",
              observed=f"{z:.2f}", expected="<= 3.5 normal, 3.5-6 observe, > 6 escalate")
    else:
        r.add("RK-003", "Amount anomaly (robust z-score)", "skip", "not a money action or fewer than 5 past transactions")

    if is_money and payee:
        seen = any(t.payee == payee for t in registry.txns(agent_id))
        r.add("RK-004", "New payee", "pass" if seen else "observe",
              "paid before" if seen else "first payment to this payee by this agent", observed=payee)
    else:
        r.add("RK-004", "New payee", "skip", "no payee on this action")

    onboarded = registry.onboarded.get(agent_id)
    current = digest(manifest)
    if onboarded is None:
        r.add("RK-005", "Mandate drift since onboarding", "review", "agent was never onboarded with this verifier")
    else:
        same = onboarded == current
        r.add("RK-005", "Mandate drift since onboarding", "pass" if same else "review",
              "manifest unchanged since onboarding" if same else "manifest changed since onboarding: re-confirm with the principal",
              observed=current[:19] + "...", expected=onboarded[:19] + "...")

    instruction = action["instruction"]["text"]
    stated = stated_amounts(instruction)
    if is_money and stated:
        ok = any(abs(amount - s) <= max(100, s // 100) for s in stated)
        r.add("RK-006", "Matches the principal's instruction", "pass" if ok else "fail",
              f"instruction says {', '.join(rupees(s) for s in sorted(stated))}; action is {rupees(amount)}",
              observed=amount, expected=sorted(stated))
    else:
        r.add("RK-006", "Matches the principal's instruction", "skip", "instruction states no amount, or not a money action")

    untrusted = " ".join(s.get("content", "") + " " + s["summary"] for s in action["trace"]
                         if s["source"] in ("untrusted_web", "untrusted_document"))
    allowed_payees = {p["value"] for p in manifest["mandate"]["allowed_payees"]}
    tainted = []
    if untrusted:
        if payee and payee.lower() in untrusted.lower() and payee.lower() not in instruction.lower() and payee not in allowed_payees:
            tainted.append(f"payee {payee}")
        if is_money and amount > 0 and amount in loose_amounts(untrusted) and amount not in stated:
            tainted.append(f"amount {rupees(amount)}")
    r.add("RK-007", "Untrusted-content taint", "fail" if tainted else ("pass" if untrusted else "skip"),
          f"{' and '.join(tainted)} came from untrusted content, not from the principal" if tainted else
          ("untrusted content present but did not supply action values" if untrusted else "no untrusted content in trace"),
          observed=tainted or None)

    hits = sorted({m.group(0) for rx in _INJ for m in rx.finditer(untrusted)})
    r.add("RK-008", "Prompt-injection markers", "review" if hits else ("pass" if untrusted else "skip"),
          f"instruction-like text in untrusted content: {hits}" if hits else
          ("no markers found" if untrusted else "no untrusted content in trace"), observed=hits or None)
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
    manifest = json.load(open(a.manifest, encoding="utf-8"))
    reg = demo_registry()
    reg.onboard(manifest)
    res = run(manifest, json.load(open(a.action, encoding="utf-8")), reg, datetime.fromisoformat(a.now))
    print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
    return 0 if res.decision != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
