"""Combine gate results into one of SAFR's four outcomes.

SAFR v1.1 defines Deny, Escalate, Auto-Execute and Observe. Mapping used here:

- any gate FAIL            -> DENY          (hard constraint or risk above threshold)
- else any gate REVIEW     -> ESCALATE      (in scope, but above autonomous threshold)
- else any gate OBSERVE    -> OBSERVE       (executes, flagged for later review)
- else                     -> AUTO_EXECUTE
"""
from __future__ import annotations

from typing import Iterable

from gates.base import GateResult

DENY, ESCALATE, OBSERVE, AUTO_EXECUTE = "DENY", "ESCALATE", "OBSERVE", "AUTO_EXECUTE"


def dispose(results: Iterable[GateResult]) -> str:
    decisions = {r.decision for r in results}
    if "FAIL" in decisions:
        return DENY
    if "REVIEW" in decisions:
        return ESCALATE
    if "OBSERVE" in decisions:
        return OBSERVE
    return AUTO_EXECUTE
