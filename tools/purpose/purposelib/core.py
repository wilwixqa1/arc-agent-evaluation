"""Purpose documents: canonicalize, seal, validate, score.

Three jobs:

1. **Seal.** Canonicalize per RFC 8785 (JSON Canonicalization Scheme) and hash with
   SHA-256, so a purpose can be bound on-chain before the outcome exists and verified
   afterward by anyone. RFC 8785 is chosen deliberately: the IETF agent audit trail
   draft uses the same canonicalization, so a sealed purpose drops into that ecosystem
   without translation.

2. **Validate.** Structural validation against the JSON Schema, plus semantic checks
   the schema cannot express.

3. **Score specificity.** A purpose written by the agent that will be judged on it has
   an obvious incentive to be vague. Specificity is computed from the document alone,
   before any response exists, so it cannot be influenced by the outcome. Tracking it
   over time is the drift metric: if stated purposes get vaguer as agents learn how
   they are graded, that shows up here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "spec" / "purpose.schema.json"

# A concrete referent is a number, a quantity, a hex address, a date, an identifier,
# or a quoted literal. Criteria containing none of these tend to be unfalsifiable.
CONCRETE_RE = re.compile(
    r"(0x[a-fA-F0-9]{6,})"           # addresses, hashes
    r"|(\b\d{4}-\d{2}-\d{2}\b)"      # dates
    r"|(\b\d+(\.\d+)?\s*%)"          # percentages
    r"|(\b\d+(\.\d+)?\b)"            # bare numbers
    r"|(\"[^\"]{2,}\")"              # quoted literals
    r"|(\b[A-Z]{2,}[A-Za-z0-9_]*\b)" # acronyms and identifiers
)

# Phrases that make a criterion unfalsifiable no matter what follows them.
HEDGE_RE = re.compile(
    r"\b(reasonabl\w+|appropriat\w+|adequat\w+|sufficient\w*|good|useful|helpful|"
    r"relevant|high[- ]quality|as expected|sensible|acceptable|properly|correctly)\b",
    re.I,
)


# --------------------------------------------------------------------------
# RFC 8785 canonicalization
# --------------------------------------------------------------------------

def _canon_number(n: int | float) -> str:
    """RFC 8785 numbers are ECMAScript Number::toString of the double value."""
    if isinstance(n, bool):
        raise TypeError("bool is not a number")
    if isinstance(n, int):
        return str(n)
    if math.isnan(n) or math.isinf(n):
        raise ValueError("NaN and Infinity are not serializable")
    if n == int(n) and abs(n) < 1e21:
        return str(int(n))
    out = repr(float(n))
    return out


def canonicalize(obj: Any) -> bytes:
    """Serialize per RFC 8785: sorted keys by UTF-16 code unit, no whitespace,
    minimal escaping, ECMAScript number formatting."""

    def enc(o: Any) -> str:
        if o is None:
            return "null"
        if o is True:
            return "true"
        if o is False:
            return "false"
        if isinstance(o, (int, float)):
            return _canon_number(o)
        if isinstance(o, str):
            return json.dumps(o, ensure_ascii=False, separators=(",", ":"))
        if isinstance(o, list):
            return "[" + ",".join(enc(v) for v in o) + "]"
        if isinstance(o, dict):
            items = sorted(o.items(), key=lambda kv: kv[0].encode("utf-16-be"))
            return "{" + ",".join(f"{enc(k)}:{enc(v)}" for k, v in items) + "}"
        raise TypeError(f"not JSON serializable: {type(o).__name__}")

    return enc(obj).encode("utf-8")


def purpose_hash(doc: dict) -> str:
    """SHA-256 over the canonicalized document with `binding` removed.

    Removing the whole binding block, rather than blanking one field, means the seal
    is stable no matter what settlement metadata gets attached afterward: a purpose
    sealed off-chain and the same purpose later written to a job have identical
    hashes.
    """
    body = {k: v for k, v in doc.items() if k != "binding"}
    return "0x" + hashlib.sha256(canonicalize(body)).hexdigest()


def seal(doc: dict, sealed_at: str | None = None, on_chain: dict | None = None) -> dict:
    """Return a copy of the document with its binding block filled in."""
    out = {k: v for k, v in doc.items() if k != "binding"}
    binding = {
        "canonicalization": "RFC8785",
        "hashAlgorithm": "SHA-256",
        "purposeHash": purpose_hash(out),
    }
    if sealed_at:
        binding["sealedAt"] = sealed_at
    if on_chain is not None:
        binding["onChain"] = on_chain
    out["binding"] = binding
    return out


def verify_seal(doc: dict) -> tuple[bool, str]:
    binding = doc.get("binding") or {}
    claimed = binding.get("purposeHash")
    if not claimed:
        return False, "no purposeHash present"
    actual = purpose_hash(doc)
    if claimed != actual:
        return False, f"hash mismatch: claims {claimed}, computes {actual}"
    return True, actual


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def load_schema(path: Path | None = None) -> dict:
    return json.loads((path or SCHEMA_PATH).read_text())


def validate(doc: dict, schema: dict | None = None) -> ValidationResult:
    """Schema validation plus the semantic rules JSON Schema cannot express."""
    from jsonschema import Draft202012Validator, FormatChecker

    schema = schema or load_schema()
    errors = [
        f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc),
            key=lambda e: list(e.path),
        )
    ]
    warnings: list[str] = []
    obj = doc.get("objective") or {}

    # Criterion ids must be unique; verdicts reference them individually.
    for key, prefix in (("successCriteria", "s"), ("disqualifiers", "d")):
        ids = [c.get("id") for c in obj.get(key, [])]
        if len(ids) != len(set(ids)):
            errors.append(f"objective/{key}: duplicate ids {ids}")

    # A criterion that restates the summary is not a criterion.
    summary = (doc.get("task") or {}).get("summary", "").strip().lower()
    for c in obj.get("successCriteria", []):
        if summary and c.get("statement", "").strip().lower() == summary:
            errors.append(f"objective/successCriteria/{c.get('id')}: restates task.summary")

    # Hedge words make a criterion unfalsifiable. Warn rather than reject: sometimes
    # the hedge is qualified by something concrete in the same sentence.
    for key in ("successCriteria", "disqualifiers"):
        for c in obj.get(key, []):
            st = c.get("statement", "")
            hedges = sorted({h.group(0).lower() for h in HEDGE_RE.finditer(st)})
            if hedges and not CONCRETE_RE.search(st):
                warnings.append(
                    f"objective/{key}/{c.get('id')}: hedge {hedges} with no concrete referent"
                )

    # A purpose whose constraints block is entirely empty has nothing deterministic
    # to check, which pushes the whole burden onto the judge.
    con = doc.get("constraints") or {}
    if not any(v for v in con.values()):
        warnings.append("constraints: empty, so nothing is machine-checkable")

    # Blinding off is legal but should never be silent.
    bl = ((doc.get("evaluation") or {}).get("blinding") or {})
    off = [k for k, v in bl.items() if v is False]
    if off:
        warnings.append(f"evaluation/blinding: disabled for {off}, results may carry halo effects")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


# --------------------------------------------------------------------------
# Specificity
# --------------------------------------------------------------------------

@dataclass
class Specificity:
    score: float
    components: dict[str, float]
    detail: dict[str, Any]


def specificity(doc: dict) -> Specificity:
    """Score 0..1 for how falsifiable this purpose is, computed from the document
    alone.

    Deliberately transparent and boring. The point is not that the weights are
    optimal, it is that the number is reproducible, outcome-independent, and
    trackable over time. Every component is a count the reader can verify by hand.
    """
    obj = doc.get("objective") or {}
    con = doc.get("constraints") or {}
    crits = obj.get("successCriteria", [])
    disqs = obj.get("disqualifiers", [])

    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    # 1. Enough independently gradeable criteria. Saturates at 5.
    c_count = clamp(len(crits) / 5.0)

    # 2. Disqualifiers present. Hardest field to fake, weighted accordingly.
    d_count = clamp(len(disqs) / 3.0)

    # 3. Criteria that name something concrete rather than gesturing at quality.
    statements = [c.get("statement", "") for c in crits] + [d.get("statement", "") for d in disqs]
    concrete = sum(1 for s in statements if CONCRETE_RE.search(s))
    c_concrete = concrete / len(statements) if statements else 0.0

    # 4. Absence of unqualified hedging.
    hedged = sum(1 for s in statements if HEDGE_RE.search(s) and not CONCRETE_RE.search(s))
    c_unhedged = 1.0 - (hedged / len(statements)) if statements else 0.0

    # 5. Deterministic surface: how much can be checked without a judge at all.
    checkable = 0
    checkable += 1 if con.get("responseSchemaRef") else 0
    checkable += 1 if con.get("requiredFields") else 0
    checkable += 1 if con.get("numericBounds") else 0
    checkable += 1 if con.get("requiredSubstrings") else 0
    checkable += 1 if con.get("responseFormat") else 0
    checkable += 1 if con.get("freshness") else 0
    c_checkable = clamp(checkable / 4.0)

    # 6. Concrete referents in the task itself.
    inputs = (doc.get("task") or {}).get("inputs") or {}
    c_inputs = clamp(len(inputs) / 3.0)

    components = {
        "criteria_count": c_count,
        "disqualifiers": d_count,
        "concrete_referents": c_concrete,
        "unhedged": c_unhedged,
        "machine_checkable": c_checkable,
        "task_inputs": c_inputs,
    }
    weights = {
        "criteria_count": 0.15,
        "disqualifiers": 0.25,
        "concrete_referents": 0.20,
        "unhedged": 0.15,
        "machine_checkable": 0.15,
        "task_inputs": 0.10,
    }
    score = sum(components[k] * weights[k] for k in weights)

    return Specificity(
        score=round(score, 3),
        components={k: round(v, 3) for k, v in components.items()},
        detail={
            "n_criteria": len(crits),
            "n_disqualifiers": len(disqs),
            "n_statements_with_concrete_referent": concrete,
            "n_statements_hedged_without_referent": hedged,
            "n_checkable_constraint_kinds": checkable,
            "n_task_inputs": len(inputs),
        },
    )
