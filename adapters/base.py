"""What every adapter does with a KYA decision.

AUTO_EXECUTE / OBSERVE -> a rail-shaped request (mock) carrying the KYA evidence reference
ESCALATE               -> a hold message for a human approver, nothing sent to the rail
DENY                   -> a refusal with rule ids, nothing sent to the rail
"""
from __future__ import annotations

from typing import Any

from kya.canonical import digest


def kya_reference(manifest: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Compact, privacy-safe pointer to the evidence. No personal data, only ids and digests."""
    return {
        "agent_id": manifest["identity"]["agent_id"],
        "manifest_digest": digest(manifest),
        "mandate_id": manifest["mandate"]["mandate_id"],
        "disposition": result["outcome"],
        "evidence_hash": result["evidence_hash"],
    }


def not_sent(result: dict[str, Any], rail: str) -> dict[str, Any] | None:
    if result["outcome"] == "DENY":
        return {"rail": rail, "sent": False, "status": "refused", "reason_rules": result["basis_rules"]}
    if result["outcome"] == "ESCALATE":
        return {"rail": rail, "sent": False, "status": "held_for_human_approval", "reason_rules": result["basis_rules"]}
    return None


def inr(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"
