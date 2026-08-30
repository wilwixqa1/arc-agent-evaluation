"""Verdict derivation.

The judge answers narrow yes/no questions. The overall verdict is computed here, by a
stated rule, with no model involved. Keeping the rule out of the prompt matters: a
judge that knew how answers combine could reason backward toward a preferred outcome.

Rule order is significant. First match wins. See spec/rubric/v0.1.0.md §2.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

CriterionAnswer = Literal["met", "not_met", "unclear"]
DisqualifierAnswer = Literal["triggered", "not_triggered", "unclear"]
Verdict = Literal["served", "partially_served", "not_served", "no_response", "constraint_violated"]

RUBRIC_VERSION = "0.1.0"


@dataclass
class JudgeAnswers:
    """One judge's answers for one response."""
    criteria: dict[str, CriterionAnswer] = field(default_factory=dict)
    disqualifiers: dict[str, DisqualifierAnswer] = field(default_factory=dict)
    reasoning: dict[str, str] = field(default_factory=dict)
    raw: Any = None


@dataclass
class DerivedVerdict:
    verdict: Verdict
    rule: int
    explanation: str

    def as_dict(self) -> dict:
        return asdict(self)


def derive(
    answers: JudgeAnswers,
    purpose: dict,
    response_empty: bool = False,
    constraint_violations: list[str] | None = None,
) -> DerivedVerdict:
    violations = constraint_violations or []

    # 1. Nothing came back.
    if response_empty:
        return DerivedVerdict("no_response", 1, "response was empty or the request errored")

    # 2. Hard constraints outrank the judge entirely.
    if violations:
        return DerivedVerdict(
            "constraint_violated", 2,
            f"hard constraint(s) violated: {', '.join(violations)}",
        )

    obj = purpose.get("objective") or {}
    crits = obj.get("successCriteria", [])
    by_id = {c["id"]: c for c in crits}

    # 3. Any disqualifier firing is fatal. This is why disqualifiers are required.
    fired = [k for k, v in answers.disqualifiers.items() if v == "triggered"]
    if fired:
        return DerivedVerdict("not_served", 3, f"disqualifier(s) triggered: {', '.join(sorted(fired))}")

    met = [k for k, v in answers.criteria.items() if v == "met"]
    not_met = [k for k, v in answers.criteria.items() if v == "not_met"]
    unclear = [k for k, v in answers.criteria.items() if v == "unclear"]

    # 4. Nothing was met.
    if not met:
        return DerivedVerdict("not_served", 4, "no success criterion was met")

    # 5. A necessary criterion that is not confirmed met caps the verdict.
    #    `unclear` does not pass: a necessary criterion the judge cannot confirm is
    #    not a criterion that was met.
    blocked = sorted(
        k for k in (not_met + unclear)
        if by_id.get(k, {}).get("necessary", False)
    )
    if blocked:
        return DerivedVerdict(
            "partially_served", 5,
            f"necessary criteria not confirmed met: {', '.join(blocked)}",
        )

    # 6. Clean sweep.
    if len(met) == len(crits) and not not_met and not unclear:
        return DerivedVerdict("served", 6, f"all {len(crits)} success criteria met")

    # 7. Mixed.
    return DerivedVerdict(
        "partially_served", 7,
        f"{len(met)} of {len(crits)} criteria met, {len(not_met)} not met, {len(unclear)} unclear",
    )


def aggregate(verdicts: list[str]) -> dict:
    """Modal verdict across repeats, with the self-consistency share.

    The consistency figure is published alongside the verdict, never hidden.
    Presenting a 2-of-3 verdict as unanimous is the fake determinism this project
    criticizes in numeric reputation scores.
    """
    if not verdicts:
        return {"modal_verdict": None, "consistency": 0.0, "n": 0, "distribution": {}}
    counts = Counter(verdicts)
    modal, top = counts.most_common(1)[0]
    return {
        "modal_verdict": modal,
        "consistency": round(top / len(verdicts), 3),
        "unanimous": top == len(verdicts),
        "n": len(verdicts),
        "distribution": dict(counts),
    }


def criterion_consistency(runs: list[JudgeAnswers]) -> dict[str, dict]:
    """Per-criterion agreement across repeats. Localizes disagreement to specific
    criteria rather than whole responses, which is what tells a purpose author that
    a particular criterion is badly written."""
    out: dict[str, dict] = {}
    keys = {k for r in runs for k in r.criteria} | {k for r in runs for k in r.disqualifiers}
    for k in sorted(keys):
        vals = [
            (r.criteria.get(k) or r.disqualifiers.get(k))
            for r in runs
            if k in r.criteria or k in r.disqualifiers
        ]
        if not vals:
            continue
        counts = Counter(vals)
        modal, top = counts.most_common(1)[0]
        out[k] = {
            "modal": modal,
            "consistency": round(top / len(vals), 3),
            "distribution": dict(counts),
        }
    return out
