import copy

import pytest

from kya.canonical import canonical_bytes, digest
from kya.crypto import SignatureError, sign_detached, verify_detached
from kya.demo_keys import agent_key, issuer_key, verifier_key
from kya.evidence import EvidenceLedger


def test_canonical_json_is_order_independent_and_rejects_floats():
    assert canonical_bytes({"b": 1, "a": [2, "₹"]}) == canonical_bytes({"a": [2, "₹"], "b": 1})
    assert canonical_bytes({"a": "₹"}) == '{"a":"₹"}'.encode()
    with pytest.raises(ValueError):
        canonical_bytes({"amount": 12.5})


def test_detached_jws_round_trip_and_tamper():
    k = agent_key("did:web:x.example:a")
    obj = {"a": 1, "b": "two"}
    obj["proof"] = sign_detached(obj, k, "kya-action+jws")
    assert ".." in obj["proof"]["jws"]
    verify_detached(obj, k.public, "kya-action+jws")
    bad = copy.deepcopy(obj)
    bad["a"] = 2
    with pytest.raises(SignatureError):
        verify_detached(bad, k.public, "kya-action+jws")
    with pytest.raises(SignatureError, match="typ"):
        verify_detached(obj, k.public, "kya-manifest+jws")
    with pytest.raises(SignatureError):
        verify_detached(obj, issuer_key("did:web:other.example").public, "kya-action+jws")


def test_ledger_chain_detects_edit_delete_and_reorder():
    led = EvidenceLedger(verifier_key())
    for i in range(5):
        led.append("event", {"i": i})
    assert led.verify()["ok"]

    edited = copy.deepcopy(led)
    edited.records[2]["body"]["i"] = 99
    assert edited.verify() == {"ok": False, "checked": 3, "broken_at": 3, "reason": "body was modified after it was recorded"}

    deleted = copy.deepcopy(led)
    del deleted.records[1]
    assert deleted.verify()["broken_at"] == 3

    swapped = copy.deepcopy(led)
    swapped.records[1], swapped.records[2] = swapped.records[2], swapped.records[1]
    assert not swapped.verify()["ok"]


def test_ledger_rejects_rehashed_forgery_without_signing_key():
    """An attacker who edits a record AND recomputes its hash still fails the signature check."""
    from kya.canonical import sha256_hex
    led = EvidenceLedger(verifier_key())
    led.append("event", {"outcome": "DENY"})
    rec = led.records[0]
    rec["body"]["outcome"] = "AUTO_EXECUTE"
    rec["body_digest"] = digest(rec["body"])
    rec["hash"] = sha256_hex(canonical_bytes({k: v for k, v in rec.items() if k not in ("hash", "sig")}))
    assert led.verify()["reason"] == "verifier signature invalid"
