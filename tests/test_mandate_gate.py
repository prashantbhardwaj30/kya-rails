import copy
from datetime import timedelta

from gates import mandate_gate
from kya.registry import Txn

from .conftest import load


def outcome(res, rule):
    return next(c.outcome for c in res.checks if c.rule_id == rule)


def test_valid_examples_pass(registry, now):
    for name in ("credit-bureau-check", "loan-disbursal", "upi-agent-payment", "whatsapp-commerce"):
        res = mandate_gate.run(load(f"valid/{name}.manifest.json"), load(f"valid/{name}.action.json"), registry, now)
        assert res.decision == "PASS", (name, res.to_dict()["failed_rules"])


def test_unauthorised_action_type(registry, now, household):
    m, a = household
    a = copy.deepcopy(a)
    a["action_type"] = "payment.link_create"
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-001") == "fail"


def test_delegation_too_deep(registry, now, disbursal):
    m, a = copy.deepcopy(disbursal[0]), disbursal[1]
    m["authority"]["delegation"] = {"depth": 2, "max_depth": 1}
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-002") == "fail"


def test_mandate_window(registry, disbursal):
    m, a = disbursal
    from kya.defaults import DEMO_NOW
    assert outcome(mandate_gate.run(m, a, registry, DEMO_NOW + timedelta(days=100)), "MD-003") == "fail"


def test_per_txn_cap_and_hitl(registry, now, household):
    m, a = household
    a = copy.deepcopy(a)
    a["params"]["amount_paise"] = 160000  # Rs 1,600: under Rs 2,000 cap, over Rs 1,500 approval line
    res = mandate_gate.run(m, a, registry, now)
    assert outcome(res, "MD-005") == "pass" and outcome(res, "MD-012") == "review"
    a["params"]["amount_paise"] = 250000
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-005") == "fail"


def test_aggregate_cap_counts_spend_since_mandate_start(registry, now, household):
    m, a = household
    agent = m["identity"]["agent_id"]
    for i in range(6):
        registry.record_txn(agent, Txn(now - timedelta(hours=i + 1), 150000, "freshkart.pune@kyabank", "household_purchase"))
    res = mandate_gate.run(m, a, registry, now)  # 9,000 spent + 1,249 > 10,000 block
    assert outcome(res, "MD-006") == "fail"


def test_merchant_category_and_payee(registry, now, household):
    m, a = household
    a = copy.deepcopy(a)
    a["params"]["merchant_category"] = "7995"  # gambling
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-007") == "fail"
    a = copy.deepcopy(household[1])
    a["params"]["payee"] = {"type": "vpa", "value": "unknown.shop@kyabank"}
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-008") == "fail"


def test_open_payee_mandate_skips_payee_rule(registry, now):
    m, a = load("valid/whatsapp-commerce.manifest.json"), load("valid/whatsapp-commerce.action.json")
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-008") == "skip"


def test_dpdp_purpose_limitation_and_minimisation(registry, now, underwriting):
    m = underwriting[0]
    res = mandate_gate.run(m, load("attacks/purpose-misuse.action.json"), registry, now)
    assert res.to_dict()["failed_rules"] == ["MD-004", "MD-010", "MD-011"]


def test_dpdp_consent_withdrawn_or_expired(registry, now, underwriting):
    m, a = copy.deepcopy(underwriting[0]), underwriting[1]
    m["mandate"]["consent"]["withdrawn"] = True
    assert outcome(mandate_gate.run(m, a, registry, now), "MD-009") == "fail"
    m["mandate"]["consent"]["withdrawn"] = False
    assert outcome(mandate_gate.run(m, a, registry, now + timedelta(days=40)), "MD-009") == "fail"


def test_injected_payee_attack(registry, now, disbursal):
    res = mandate_gate.run(disbursal[0], load("attacks/injected-payee.action.json"), registry, now)
    d = res.to_dict()
    assert d["failed_rules"] == ["MD-008"] and d["review_rules"] == ["MD-012"]
