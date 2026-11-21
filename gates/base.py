"""Shared result types for the gates.

Every rule produces a Check with a stable rule_id, so an auditor can grep the evidence log
for, say, MD-007 across a year of decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

Outcome = Literal["pass", "fail", "review", "observe", "skip"]
Decision = Literal["PASS", "FAIL", "REVIEW", "OBSERVE"]


@dataclass
class Check:
    rule_id: str
    title: str
    outcome: Outcome
    detail: str
    observed: Any = None
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class GateResult:
    gate: str
    checks: list[Check] = field(default_factory=list)

    @property
    def decision(self) -> Decision:
        outcomes = {c.outcome for c in self.checks}
        if "fail" in outcomes:
            return "FAIL"
        if "review" in outcomes:
            return "REVIEW"
        if "observe" in outcomes:
            return "OBSERVE"
        return "PASS"

    def add(self, rule_id: str, title: str, outcome: Outcome, detail: str, observed: Any = None, expected: Any = None) -> Check:
        c = Check(rule_id, title, outcome, detail, observed, expected)
        self.checks.append(c)
        return c

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "decision": self.decision,
            "checks": [c.to_dict() for c in self.checks],
            "failed_rules": [c.rule_id for c in self.checks if c.outcome == "fail"],
            "review_rules": [c.rule_id for c in self.checks if c.outcome == "review"],
            "observe_rules": [c.rule_id for c in self.checks if c.outcome == "observe"],
        }


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def rupees(paise: int) -> str:
    """Indian digit grouping, e.g. 15000000 paise -> 'Rs 1,50,000'."""
    whole, frac = divmod(int(paise), 100)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"Rs {s}" + (f".{frac:02d}" if frac else "")
