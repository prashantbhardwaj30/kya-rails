"""Demo scenarios built from the committed examples in spec/examples.

Each run gets a fresh action_id and timestamp and is re-signed with the agent's demo key, so
scenarios can be replayed without tripping the replay rule, except in the dedicated replay
scenario, which resubmits the last envelope byte for byte.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from kya.crypto import sign_detached
from kya.demo_keys import agent_key

EXAMPLES = Path(__file__).resolve().parent.parent / "spec" / "examples"


@lru_cache(maxsize=None)
def load(rel: str) -> dict[str, Any]:
    return json.loads((EXAMPLES / rel).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Scenario:
    id: str
    group: str
    title: str
    subtitle: str
    manifest: str
    action: str | None
    adapter: str | None
    expect: str
    caption: str  # short Hinglish caption for YouTube subtitles
    mutate: str | None = None


SCENARIOS: list[Scenario] = [
    Scenario("onboard", "1 · Onboard", "Onboard four agents",
             "Verify each manifest: schema, issuer, signature, expiry, revocation. Register the approved ones.",
             "", None, None, "PASS",
             "Pehle agent ka KYA: kaun hai, kiske liye kaam karta hai, kitni authority hai."),
    Scenario("credit_check", "2 · Legitimate", "Credit bureau check",
             "Underwriting agent pulls a bureau report with DPDP consent for loan_underwriting.",
             "valid/credit-bureau-check.manifest.json", "valid/credit-bureau-check.action.json", None, "AUTO_EXECUTE",
             "Consent hai, purpose match karta hai, bureau report pull ho gaya."),
    Scenario("disbursal", "2 · Legitimate", "Loan disbursal Rs 1,50,000",
             "Disbursal agent pays the sanctioned amount to the borrower's own verified account.",
             "valid/loan-disbursal.manifest.json", "valid/loan-disbursal.action.json", "npci_upi", "AUTO_EXECUTE",
             "Sanctioned amount, verified account, mandate ke andar. Paisa chala gaya."),
    Scenario("upi", "2 · Legitimate", "UPI groceries Rs 1,249",
             "Household agent debits a Reserve Pay-style block at an approved grocer (mock UPI rail).",
             "valid/upi-agent-payment.manifest.json", "valid/upi-agent-payment.action.json", "npci_upi", "AUTO_EXECUTE",
             "Rs 10,000 ka block, approved dukaan, chhota amount. Auto-execute."),
    Scenario("whatsapp", "2 · Legitimate", "WhatsApp payment link Rs 1,899",
             "Merchant's chat agent creates a payment link for a catalogue item (mock Razorpay-style link).",
             "valid/whatsapp-commerce.manifest.json", "valid/whatsapp-commerce.action.json", "whatsapp_razorpay", "AUTO_EXECUTE",
             "Chat mein hi payment link, catalogue price par."),
    Scenario("escalate", "2 · Legitimate", "Large disbursal Rs 3,50,000",
             "In scope and under the cap, but above the Rs 2,00,000 human-approval threshold.",
             "valid/loan-disbursal.manifest.json", "valid/loan-disbursal.action.json", "npci_upi", "ESCALATE",
             "Mandate ke andar hai, par bada amount hai. Insaan approve karega.", mutate="large_disbursal"),
    Scenario("injection", "3 · Attacks", "Prompt-injected payee",
             "A salary-slip PDF tells the agent to send Rs 4,80,000 to a different VPA.",
             "valid/loan-disbursal.manifest.json", "attacks/injected-payee.action.json", "npci_upi", "DENY",
             "PDF ke andar chhupa instruction. Agent bhatak gaya, gate ne pakad liya."),
    Scenario("forged", "3 · Attacks", "Forged agent credential",
             "A look-alike disbursal agent with a manifest from an untrusted issuer and no payee limits.",
             "attacks/forged-issuer.manifest.json", "attacks/forged-issuer.action.json", "npci_upi", "DENY",
             "Nakli agent, nakli issuer. Signature match hi nahi hua."),
    Scenario("purpose", "3 · Attacks", "Bureau data for marketing",
             "Cross-sell campaign asks the underwriting agent for bureau data: outside the consented purpose.",
             "valid/credit-bureau-check.manifest.json", "attacks/purpose-misuse.action.json", None, "DENY",
             "Consent loan ke liye tha, marketing ke liye nahi. DPDP purpose limitation."),
]
BY_ID = {s.id: s for s in SCENARIOS}
ONBOARD = ["valid/credit-bureau-check.manifest.json", "valid/loan-disbursal.manifest.json",
           "valid/upi-agent-payment.manifest.json", "valid/whatsapp-commerce.manifest.json"]


def fresh_action(s: Scenario, run_no: int, requested_at: str) -> dict[str, Any]:
    a = copy.deepcopy(load(s.action))
    if s.mutate == "large_disbursal":
        a["params"]["amount_paise"] = 35000000
        a["instruction"]["text"] = "Disburse the sanctioned loan of Rs 3,50,000 for application LA-55907 to the borrower's verified account."
        a["trace"][0]["summary"] = "los.get_sanction(LA-55907) -> sanctioned 350000 INR"
    a["action_id"] = f"{a['action_id']}r{run_no}"
    a["requested_at"] = requested_at
    a.pop("proof", None)
    a["proof"] = sign_detached(a, agent_key(a["agent_id"]), "kya-action+jws")
    return a


def summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Five-pillar card for the UI. Contains no personal data beyond the masked display name."""
    i, rep, auth, m, asr = (manifest[k] for k in ("identity", "representation", "authority", "mandate", "assurance"))
    return {
        "agent_name": i["agent_name"], "agent_id": i["agent_id"], "issuer": manifest["issuer"],
        "operator": i["operator"]["legal_name"],
        "represents": f"{rep['principal_display']} ({rep['principal_type']}, {rep['kyc']['status']})",
        "binding": rep["binding"]["method"],
        "authority": auth["permitted_actions"],
        "mandate": {"purpose": m["purpose"], "per_txn_max_paise": m["limits"]["per_txn_max_paise"],
                    "human_approval_above_paise": m["limits"]["human_approval_above_paise"],
                    "valid_until": m["valid_until"], "payees": [p["value"] for p in m["allowed_payees"]],
                    "consent_purposes": m["consent"]["purposes"]},
        "assurance": f"{asr['trust_tier']} · {asr['attestation']['scheme']}",
    }
