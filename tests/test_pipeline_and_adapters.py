import copy

from adapters import atom_a2a, npci_upi, whatsapp_razorpay
from kya.pipeline import evaluate

from .conftest import load, resign_action


def test_end_to_end_dispositions(onboarded, ledger, now):
    cases = [
        ("valid/credit-bureau-check.manifest.json", "valid/credit-bureau-check.action.json", "AUTO_EXECUTE"),
        ("valid/loan-disbursal.manifest.json", "valid/loan-disbursal.action.json", "AUTO_EXECUTE"),
        ("valid/upi-agent-payment.manifest.json", "valid/upi-agent-payment.action.json", "AUTO_EXECUTE"),
        ("valid/whatsapp-commerce.manifest.json", "valid/whatsapp-commerce.action.json", "AUTO_EXECUTE"),
        ("valid/loan-disbursal.manifest.json", "attacks/injected-payee.action.json", "DENY"),
        ("valid/credit-bureau-check.manifest.json", "attacks/purpose-misuse.action.json", "DENY"),
        ("attacks/forged-issuer.manifest.json", "attacks/forged-issuer.action.json", "DENY"),
    ]
    for m, a, expected in cases:
        assert evaluate(load(m), load(a), onboarded, ledger, now)["outcome"] == expected, a
    assert ledger.verify()["ok"]


def test_identity_failure_short_circuits_and_is_logged(onboarded, ledger, now):
    r = evaluate(load("attacks/forged-issuer.manifest.json"), load("attacks/forged-issuer.action.json"), onboarded, ledger, now)
    assert [g["gate"] for g in r["gates"]] == ["identity"]
    assert [rec["kind"] for rec in ledger.records] == ["gate_result", "disposition"]
    assert ledger.records[-1]["body"]["outcome"] == "DENY"


def test_escalate_and_observe(onboarded, ledger, now, household):
    m, a = household
    big = copy.deepcopy(a)
    big["params"]["amount_paise"] = 160000
    assert evaluate(m, resign_action(big), onboarded, ledger, now)["outcome"] == "ESCALATE"
    new_payee = copy.deepcopy(a)
    new_payee["action_id"] = "act_hh0002"
    new_payee["params"]["payee"] = {"type": "vpa", "value": "gokul.dairy@kyabank"}
    new_payee["params"]["merchant_category"] = "5499"
    onboarded.history[m["identity"]["agent_id"]] = [t for t in onboarded.history[m["identity"]["agent_id"]] if t.payee != "gokul.dairy@kyabank"]
    assert evaluate(m, resign_action(new_payee), onboarded, ledger, now)["outcome"] == "OBSERVE"


def test_executed_actions_feed_history(onboarded, ledger, now, household):
    m, a = household
    before = len(onboarded.history[m["identity"]["agent_id"]])
    evaluate(m, a, onboarded, ledger, now)
    assert len(onboarded.history[m["identity"]["agent_id"]]) == before + 1


def test_upi_adapter_sends_only_when_allowed(onboarded, ledger, now, household, disbursal):
    m, a = household
    ok = npci_upi.build_request(m, a, evaluate(m, a, onboarded, ledger, now), now)
    assert ok["sent"] and ok["request"]["flow"] == "reserve_debit" and ok["request"]["amount"] == "1249.00"
    assert ok["request"]["kya"]["evidence_hash"] == ledger.records[-1]["hash"]
    dm, da = disbursal[0], load("attacks/injected-payee.action.json")
    refused = npci_upi.build_request(dm, da, evaluate(dm, da, onboarded, ledger, now), now)
    assert refused == {"rail": npci_upi.RAIL, "sent": False, "status": "refused", "reason_rules": refused["reason_rules"]}


def test_reserve_pay_prechecks(household):
    m, a = copy.deepcopy(household[0]), household[1]
    m["mandate"]["limits"]["aggregate_max_paise"] = 2_000_000
    m["mandate"]["valid_until"] = "2027-06-01T09:00:00+05:30"
    problems = npci_upi.rail_prechecks(m, a)
    assert any("10,000" in p for p in problems) and any("90" in p for p in problems)


def test_whatsapp_adapter_link_and_finance_exclusion(onboarded, ledger, now, disbursal):
    m, a = load("valid/whatsapp-commerce.manifest.json"), load("valid/whatsapp-commerce.action.json")
    out = whatsapp_razorpay.build_request(m, a, evaluate(m, a, onboarded, ledger, now), now)
    assert out["sent"] and out["request"]["amount"] == 189900 and out["request"]["currency"] == "INR"
    assert len(out["request"]["notes"]) <= 15
    fin = copy.deepcopy(a)
    fin["params"]["merchant_category"] = "6012"
    blocked = whatsapp_razorpay.build_request(m, fin, {"outcome": "AUTO_EXECUTE", "basis_rules": [], "evidence_hash": "x"}, now)
    assert blocked["status"] == "channel_ineligible"


def test_a2a_evidence_message_hmac(ledger):
    ledger.append("disposition", {"action_id": "act_x00001", "outcome": "DENY", "basis_rules": ["MD-008"], "mandate_id": "mdt_abcdef"})
    msg = atom_a2a.wrap(ledger.records[-1], "did:web:a.example", "did:web:b.example")
    assert msg["jsonrpc"] == "2.0" and atom_a2a.verify(msg)
    msg["params"]["summary"]["outcome"] = "AUTO_EXECUTE"
    assert not atom_a2a.verify(msg)
