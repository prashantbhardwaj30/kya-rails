"""Default demo trust state: which issuers the verifier trusts and for what.

DEMO_NOW is the fixed clock used by the demo, the CLI and the tests, so the committed
examples (issued 20 Nov 2026, valid 90 days) always evaluate the same way.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .demo_keys import ISSUER_NBFC, ISSUER_PSP, issuer_key
from .registry import TrustRegistry, Txn

IST = timezone(timedelta(hours=5, minutes=30))
DEMO_NOW = datetime(2026, 11, 21, 10, 30, 0, tzinfo=IST)


def demo_registry(with_history: bool = True) -> TrustRegistry:
    reg = TrustRegistry()
    # The NBFC may vouch for its own lending agents; the PSP only for payment agents.
    reg.allow_issuer(ISSUER_NBFC, issuer_key(ISSUER_NBFC).public_jwk(), ["credit_report.pull", "loan.disburse"])
    reg.allow_issuer(ISSUER_PSP, issuer_key(ISSUER_PSP).public_jwk(),
                     ["payment.upi_p2m", "payment.reserve_debit", "payment.link_create"])
    if with_history:
        seed_history(reg)
    return reg


def seed_history(reg: TrustRegistry) -> None:
    """Plausible prior activity so velocity and amount-anomaly rules have a baseline."""
    acct = "acct:KYAB0000101:xxxxxx6789"
    disb = "did:web:agents.sahyadri-finance.example:disbursal"
    for i, rupees in enumerate([125000, 150000, 90000, 175000, 110000, 140000, 160000, 120000]):
        reg.record_txn(disb, Txn(DEMO_NOW - timedelta(days=9 - i, hours=2), rupees * 100, acct, "loan_disbursal"))
    hh = "did:web:agents.paybharat-psp.example:household"
    for i, (rupees, payee) in enumerate([(1180, "freshkart.pune@kyabank"), (420, "gokul.dairy@kyabank"), (1310, "freshkart.pune@kyabank"), (390, "gokul.dairy@kyabank")]):
        reg.record_txn(hh, Txn(DEMO_NOW - timedelta(days=7 - i * 2, hours=1), rupees * 100, payee, "household_purchase"))
    shop = "did:web:agents.paybharat-psp.example:kolhapuri-house"
    for i, rupees in enumerate([1899, 2499, 1499, 1899, 2199]):
        reg.record_txn(shop, Txn(DEMO_NOW - timedelta(days=5 - i, hours=3), rupees * 100, None, "merchant_collection"))
