"""MOCK adapter: KYA decision -> UPI-style agent payment request.

What exists today, and what this mock assumes (sources in the README):
- NPCI's Unified Agentic Protocol (UAP) for agent payments on UPI was put on hold in
  September 2026 pending RBI clearance. Its message format is not public.
- UPI Reserve Pay lets a customer block up to Rs 10,000 for one merchant for up to 90 days,
  with later debits drawn from the block (P2M only), as reported from NPCI's circular.
- NPCI's AiNxt and AtOM are NOT payment rails. AiNxt is an enterprise agent-building
  platform and AtOM orchestrates UPI change management between NPCI, banks and PSPs. See
  adapters/atom_a2a.py for the AtOM-style mapping.

So every field name below is ours. The adapter shows where KYA evidence would ride along
with a payment instruction; it is not an NPCI API client and makes no network calls.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from gates.base import parse_dt

from .base import inr, kya_reference, not_sent

RAIL = "UPI (mock, UAP-anticipating)"
RESERVE_PAY_MAX_BLOCK_PAISE = 1_000_000  # Rs 10,000, as reported
RESERVE_PAY_MAX_DAYS = 90


def rail_prechecks(manifest: dict[str, Any], action: dict[str, Any]) -> list[str]:
    """Rail-level rules the mandate itself must respect before any debit is attempted."""
    problems = []
    mdt = manifest["mandate"]
    if action["action_type"] == "payment.reserve_debit":
        if mdt["limits"]["aggregate_max_paise"] > RESERVE_PAY_MAX_BLOCK_PAISE:
            problems.append("Reserve Pay block above Rs 10,000")
        days = (parse_dt(mdt["valid_until"]) - parse_dt(mdt["valid_from"])).days
        if days > RESERVE_PAY_MAX_DAYS:
            problems.append(f"Reserve Pay block validity {days} days exceeds {RESERVE_PAY_MAX_DAYS}")
        if not action["params"].get("merchant_category"):
            problems.append("Reserve Pay is person-to-merchant only: merchant category required")
    return problems


def build_request(manifest: dict[str, Any], action: dict[str, Any], result: dict[str, Any],
                  now: datetime) -> dict[str, Any]:
    held = not_sent(result, RAIL)
    if held:
        return held
    problems = rail_prechecks(manifest, action)
    if problems:
        return {"rail": RAIL, "sent": False, "status": "rail_precheck_failed", "problems": problems}
    p = action["params"]
    if action["action_type"] == "loan.disburse":
        flow, extra = "payout_credit", {"beneficiary_ref": p["payee"]["value"]}
    else:
        flow = "reserve_debit" if action["action_type"] == "payment.reserve_debit" else "p2m_pay"
        extra = {"payee_vpa": p["payee"]["value"], "mcc": p.get("merchant_category"),
                 "block_ref": manifest["representation"]["binding"].get("binding_ref")}
    return {
        "rail": RAIL,
        "sent": True,
        "status": "mock_accepted",
        "request": {
            "flow": flow,
            "txn_ref": f"KYA{action['action_id'][4:].upper()}",
            "amount": inr(p["amount_paise"]),
            "currency": "INR",
            "payer_ref": manifest["representation"]["principal_ref"],
            "initiated_by": "agent",
            "initiated_at": now.isoformat(),
            "purpose": p["purpose"],
            **extra,
            "kya": kya_reference(manifest, result),
        },
        "customer_notification": f"Your agent {manifest['identity']['agent_name']} paid Rs {inr(p['amount_paise'])} "
                                 f"under mandate {manifest['mandate']['mandate_id']}. Reply STOP to revoke.",
    }
