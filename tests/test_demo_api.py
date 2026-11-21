import pytest
from fastapi.testclient import TestClient

from demo.app import app


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/reset")
    return c


def test_health_and_index(client):
    assert client.get("/api/health").json()["ok"] is True
    html = client.get("/").text
    assert "kya-rails" in html and "Not affiliated" in html


def test_every_scenario_reaches_its_expected_outcome(client):
    scenarios = client.get("/api/scenarios").json()
    assert len(scenarios) == 9
    for s in scenarios:
        data = client.post(f"/api/run/{s['id']}").json()
        if s["id"] == "onboard":
            assert all(o["registered"] for o in data["onboarded"])
        else:
            assert data["result"]["outcome"] == s["expect"], s["id"]
    assert client.get("/api/ledger/verify").json()["ok"] is True


def test_replay_is_denied(client):
    client.post("/api/run/upi")
    r = client.post("/api/replay").json()
    assert r["result"]["outcome"] == "DENY" and r["result"]["basis_rules"] == ["ID-010"]


def test_tamper_breaks_verification(client):
    client.post("/api/run/injection")
    client.post("/api/run/upi")
    t = client.post("/api/ledger/tamper").json()
    assert t["verify"]["ok"] is False
    assert client.get("/api/ledger/verify").json()["broken_at"] == t["tampered_seq"]


def test_custom_evaluate_endpoint(client):
    from tests.conftest import load
    body = {"manifest": load("attacks/forged-issuer.manifest.json"), "action": load("attacks/forged-issuer.action.json")}
    assert client.post("/api/evaluate", json=body).json()["outcome"] == "DENY"
    assert client.post("/api/evaluate", json={"x": 1}).status_code == 422


def test_unknown_scenario_404(client):
    assert client.post("/api/run/nope").status_code == 404
