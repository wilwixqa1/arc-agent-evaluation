"""Blinding and prompt assembly.

Two responsibilities, deliberately separated from the provider adapters so both are
testable with no API key.
"""
from __future__ import annotations

import json
import re
from typing import Any

BLINDED_KEYS = {
    "hideProvider": [
        "provider", "providerName", "service", "serviceName", "serviceId",
        "operator", "agentId", "url", "endpoint", "host", "domain", "vendor",
    ],
    "hidePrice": ["price", "priceUsdc", "cost", "costUsdc", "amount", "amountPaid", "fee", "tier"],
    "hidePhrasingId": ["phrasingId", "phrasing", "variantId", "variant", "generatorId", "seed"],
}


def blind_attempt(attempt: dict, blinding: dict) -> tuple[dict, list[str]]:
    """Strip fields the judge must not see. Returns (redacted, removed_keys).

    Operates on a copy. Nested dicts are walked, because attempt metadata is
    routinely nested one level under `meta` or `request`.
    """
    removed: list[str] = []
    drop = {k.lower() for flag, keys in BLINDED_KEYS.items() if blinding.get(flag) for k in keys}

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if k.lower() in drop:
                    removed.append(k)
                    continue
                out[k] = walk(v)
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(attempt), removed


def scrub_text(text: str, terms: list[str]) -> str:
    """Remove provider names that leak inside the response body itself.

    Field-level blinding does nothing if the body says 'Powered by AcmeAPI'. Applied
    only to terms the caller knows are identifying.
    """
    out = text
    for t in sorted([t for t in terms if t and len(t) > 2], key=len, reverse=True):
        out = re.sub(re.escape(t), "[REDACTED]", out, flags=re.I)
    return out


SYSTEM = """You evaluate whether a response served a stated purpose.

You will be given a buyer's stated goal, a list of numbered success criteria, and a \
list of numbered disqualifiers. You will then be given a response that was received.

Answer each numbered item independently. For success criteria answer exactly one of \
met, not_met, or unclear. For disqualifiers answer exactly one of triggered, \
not_triggered, or unclear.

Rules:
- Judge only against the criteria as written. Do not import your own standards for \
what a good response would be.
- Answer unclear when the response does not give you enough to decide. unclear is a \
real answer, not a failure to try.
- Treat each item on its own. Do not let your answer to one item drive another.
- Give one sentence of reasoning per item, citing what in the response led you there.
- Do not produce an overall verdict, score, rating, or summary judgment. That is \
computed elsewhere and is not your task.

Return only JSON in this exact shape, with no prose before or after:

{"criteria": {"s1": {"answer": "met", "reasoning": "..."}},
 "disqualifiers": {"d1": {"answer": "not_triggered", "reasoning": "..."}}}"""


def build_prompt(purpose: dict, response_body: Any) -> str:
    obj = purpose.get("objective") or {}
    task = purpose.get("task") or {}

    lines: list[str] = []
    lines.append("## Buyer's goal")
    lines.append(obj.get("goal", ""))
    lines.append("")
    lines.append("## What was requested")
    lines.append(task.get("summary", ""))
    if task.get("inputs"):
        lines.append("")
        lines.append("Specific referents:")
        lines.append(json.dumps(task["inputs"], indent=2))
    if obj.get("outOfScope"):
        lines.append("")
        lines.append("Explicitly not required (do not penalize absence):")
        for x in obj["outOfScope"]:
            lines.append(f"- {x}")

    lines.append("")
    lines.append("## Success criteria")
    for c in obj.get("successCriteria", []):
        lines.append(f"- {c['id']}: {c['statement']}")

    lines.append("")
    lines.append("## Disqualifiers")
    for d in obj.get("disqualifiers", []):
        lines.append(f"- {d['id']}: {d['statement']}")

    body = response_body if isinstance(response_body, str) else json.dumps(response_body, indent=2)
    lines.append("")
    lines.append("## Response received")
    lines.append("<<<RESPONSE")
    lines.append(body)
    lines.append("RESPONSE>>>")
    lines.append("")
    lines.append("Answer every item above. Return only the JSON object.")
    return "\n".join(lines)


def parse_judge_output(text: str) -> dict:
    """Extract the JSON object, tolerating code fences and stray prose."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start, depth = t.find("{"), 0
    if start == -1:
        raise ValueError(f"no JSON object in judge output: {text[:200]}")
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[start:i + 1])
    raise ValueError(f"unterminated JSON in judge output: {text[:200]}")
