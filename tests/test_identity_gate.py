import copy
from datetime import timedelta

from gates import identity_gate
from kya.crypto import sign_detached
from kya.demo_keys import ISSUER_PSP, agent_key, issuer_key

from .conftest import load, resign_action, resign_manifest


def failed(res):
    return [c.rule_id for c in res.checks if c.outcome == "fail"]


def test_all_valid_examples_pass(registry, now):
    for name in ("credit-bureau-check", "loan-disbursal", "upi-agent-payment", "whatsapp-commerce"):
        res = identity_gate.run(load(f"valid/{name}.manifest.json"), load(f"valid/{name}.action.json"), registry, now)
        assert res.decision == "PASS", (name, failed(res))
        assert [c.rule_id for c in res.checks] == [f"ID-{i:03d}" for i in range(1, 12)]


def test_forged_issuer_is_rejected_and_signature_matches_no_trusted_key(registry, now):
    res = identity_gate.run(load("attacks/forged-issuer.manifest.json"), load("attacks/forged-issuer.action.json"), registry, now)
    assert failed(res) == ["ID-003", "ID-005"]
    assert "no match" in res.checks[-1].detail or any("no match" in c.detail for c in res.checks)


def test_issuer_field_swapped_to_trusted_issuer_fails_signature(registry, now, disbursal):
    m = load("attacks/forged-issuer.manifest.json")
    m["issuer"] = "did:web:kya.sahyadri-finance.example"
    res = identity_gate.run(m, resign_action({**disbursal[1], "manifest_id": m["manifest_id"], "agent_id": m["identity"]["agent_id"]}), registry, now)
    assert "ID-005" in failed(res)


def test_tampered_mandate_breaks_issuer_signature(registry, now, disbursal):
    m, a = copy.deepcopy(disbursal[0]), disbursal[1]
    m["mandate"]["limits"]["per_txn_max_paise"] = 10**10  # agent edits its own cap
    assert failed(identity_gate.run(m, a, registry, now)) == ["ID-005"]


def test_issuer_cannot_grant_actions_outside_its_remit(registry, now, disbursal):
    m = copy.deepcopy(disbursal[0])
    m["issuer"] = ISSUER_PSP  # a PSP minting loan-disbursal authority
    m = resign_manifest(m)
    assert failed(identity_gate.run(m, disbursal[1], registry, now)) == ["ID-004"]


def test_expired_and_not_yet_valid(registry, now, disbursal):
    m, a = disbursal
    late = now + timedelta(days=120)
    assert "ID-006" in failed(identity_gate.run(m, resign_action({**a, "requested_at": late.isoformat()}), registry, late))
    early = now - timedelta(days=3)
    assert "ID-006" in failed(identity_gate.run(m, resign_action({**a, "requested_at": early.isoformat()}), registry, early))


def test_revoked_manifest(registry, now, disbursal):
    m, a = disbursal
    registry.revoke(m["issuer"], m["authority"]["revocation"]["status_list_index"])
    assert failed(identity_gate.run(m, a, registry, now)) == ["ID-007"]


def test_action_for_another_agent(registry, now, disbursal, household):
    assert "ID-008" in failed(identity_gate.run(disbursal[0], household[1], registry, now))


def test_action_signed_with_wrong_key(registry, now, disbursal):
    m, a = disbursal
    forged = resign_action(a, key=agent_key("did:web:attacker.example:bot"))
    assert "ID-009" in failed(identity_gate.run(m, forged, registry, now))


def test_replay_and_stale_timestamp(registry, now, disbursal):
    m, a = disbursal
    assert identity_gate.run(m, a, registry, now).decision == "PASS"
    assert failed(identity_gate.run(m, a, registry, now)) == ["ID-010"]
    stale = resign_action({**a, "action_id": "act_db0002", "requested_at": (now - timedelta(minutes=9)).isoformat()})
    assert failed(identity_gate.run(m, stale, registry, now)) == ["ID-010"]


def test_assurance_tier_too_low_for_lending(registry, now, underwriting):
    m, a = underwriting
    m = copy.deepcopy(m)
    m["assurance"]["trust_tier"] = "T1"
    m = resign_manifest(m)
    a = resign_action({**a, "manifest_id": m["manifest_id"]})
    assert failed(identity_gate.run(m, a, registry, now)) == ["ID-011"]


def test_schema_invalid_manifest_short_circuits(registry, now, disbursal):
    m = load("invalid/unknown-field.manifest.json")
    res = identity_gate.run(m, disbursal[1], registry, now)
    assert failed(res) == ["ID-001"]
    assert {c.rule_id for c in res.checks} == {"ID-001", "ID-002"}


def test_manifest_checks_for_onboarding(registry, now, household):
    res = identity_gate.manifest_checks(household[0], registry, now)
    assert res.decision == "PASS"
    assert [c.rule_id for c in res.checks] == ["ID-001", "ID-003", "ID-004", "ID-005", "ID-006", "ID-007"]


def test_signature_header_kid_mismatch(registry, now, disbursal):
    m = copy.deepcopy(disbursal[0])
    m.pop("proof")
    p = sign_detached(m, issuer_key(m["issuer"]), "kya-manifest+jws")
    p["kid"] = "did:web:kya.sahyadri-finance.example#key-2"
    m["proof"] = p
    assert "ID-005" in failed(identity_gate.run(m, disbursal[1], registry, now))
