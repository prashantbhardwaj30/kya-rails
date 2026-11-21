from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from kya.crypto import sign_detached
from kya.defaults import DEMO_NOW, demo_registry
from kya.demo_keys import agent_key, issuer_key, verifier_key
from kya.evidence import EvidenceLedger

EX = Path(__file__).resolve().parent.parent / "spec" / "examples"


def load(rel: str) -> dict:
    return json.loads((EX / rel).read_text(encoding="utf-8"))


def resign_manifest(m: dict) -> dict:
    m = copy.deepcopy(m)
    m.pop("proof", None)
    m["proof"] = sign_detached(m, issuer_key(m["issuer"]), "kya-manifest+jws")
    return m


def resign_action(a: dict, key=None) -> dict:
    a = copy.deepcopy(a)
    a.pop("proof", None)
    a["proof"] = sign_detached(a, key or agent_key(a["agent_id"]), "kya-action+jws")
    return a


@pytest.fixture
def now():
    return DEMO_NOW


@pytest.fixture
def registry():
    return demo_registry()


@pytest.fixture
def onboarded(registry):
    for name in ("credit-bureau-check", "loan-disbursal", "upi-agent-payment", "whatsapp-commerce"):
        registry.onboard(load(f"valid/{name}.manifest.json"))
    return registry


@pytest.fixture
def ledger():
    return EvidenceLedger(verifier_key(), clock=lambda: DEMO_NOW)


@pytest.fixture
def disbursal():
    return load("valid/loan-disbursal.manifest.json"), load("valid/loan-disbursal.action.json")


@pytest.fixture
def household():
    return load("valid/upi-agent-payment.manifest.json"), load("valid/upi-agent-payment.action.json")


@pytest.fixture
def underwriting():
    return load("valid/credit-bureau-check.manifest.json"), load("valid/credit-bureau-check.action.json")
