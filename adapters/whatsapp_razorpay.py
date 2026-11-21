"""MOCK adapter: KYA decision -> Meta Business Agent + Razorpay-style payment link.

Grounding (links in the README):
- Razorpay went live on Meta Business Agent on WhatsApp in India on 17 Nov 2026: when the
  customer is ready to buy, the agent generates a Razorpay payment link in the chat, and the
  business owner can step into any conversation.
- Meta's developer docs list verticals that are NOT eligible for Meta Business Agent,
  including Finance. So a lending agent cannot use this channel; the adapter refuses
  financial-services MCCs instead of silently sending.
- The request body mirrors the public shape of Razorpay's Create Payment Link API
  (amount in paise, currency, description, customer, notify, reminder_enable, notes,
  expire_by, reference_id). Nothing is sent; there is no Razorpay key in this repo.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .base import kya_reference, not_sent

RAIL = "WhatsApp + payment link (mock)"
# ISO 18245 financial-services MCCs (6010-6012 financial institutions, 6051 quasi-cash, 6211 securities).
INELIGIBLE_MCC = {"6010", "6011", "6012", "6051", "6211"}


def build_request(manifest: dict[str, Any], action: dict[str, Any], result: dict[str, Any],
                  now: datetime) -> dict[str, Any]:
    if action["action_type"] != "payment.link_create":
        return {"rail": RAIL, "sent": False, "status": "not_applicable", "problems": ["only payment.link_create maps to this channel"]}
    mcc = action["params"].get("merchant_category")
    if mcc in INELIGIBLE_MCC:
        return {"rail": RAIL, "sent": False, "status": "channel_ineligible",
                "problems": [f"MCC {mcc} is financial services; Meta Business Agent excludes the Finance vertical"]}
    held = not_sent(result, RAIL)
    if held:
        if held["status"] == "held_for_human_approval":
            held["chat_message"] = "Let me check this with the owner, I'll get back to you shortly."
            held["handoff"] = "owner"
        return held
    p, ref = action["params"], kya_reference(manifest, result)
    return {
        "rail": RAIL,
        "sent": True,
        "status": "mock_link_created",
        "request": {
            "amount": p["amount_paise"],
            "currency": "INR",
            "accept_partial": False,
            "reference_id": action["action_id"],
            "description": f"WhatsApp order {action['action_id']} ({manifest['identity']['agent_name']})"[:120],
            "expire_by": int((now + timedelta(minutes=30)).timestamp()),
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {"kya_agent": ref["agent_id"][-60:], "kya_mandate": ref["mandate_id"],
                      "kya_evidence": ref["evidence_hash"][:32]},
        },
        "chat_message": f"Here is your secure payment link for Rs {p['amount_paise'] // 100:,}: "
                        f"https://pay.mock.example/{action['action_id']}",
        "kya": ref,
    }
