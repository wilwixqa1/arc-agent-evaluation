"""Assemble a verdict record.

Ties together the deterministic constraint pass, the judge's per-item answers, and
the derived verdict into the canonical published artifact (spec/verdict.schema.json).

The verdict is hashed the same way a purpose is: RFC 8785 canonicalization, SHA-256,
excluding the mutable `onChain` block. That gives a bytes32 that drops straight into
the ERC-8183 `reason` slot at complete/reject.
"""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .constraints import check as check_constraints
from .verdict import JudgeAnswers, RUBRIC_VERSION, aggregate, criterion_consistency, derive

# Reuse the purpose canonicalizer rather than reimplementing RFC 8785 twice.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "purpose"))
from purposelib.core import canonicalize  # noqa: E402

SCHEMA_VERSION = "0.1.0"


def sha256_hex(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()


def verdict_hash(record: dict) -> str:
    """Hash over the record with `onChain` removed, so writing the verdict on-chain
    does not change the hash being written."""
    body = {k: v for k, v in record.items() if k != "onChain"}
    return sha256_hex(canonicalize(body))


def build_record(
    purpose: dict,
    attempt: dict,
    answers: JudgeAnswers,
    *,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = 0.0,
    blinding_applied: dict | None = None,
    latency_ms: int | None = None,
    repeat_index: int = 0,
    prompt: str | None = None,
) -> dict:
    cres = check_constraints(purpose, attempt)
    body = attempt.get("body")
    empty = body in (None, "", {}, []) or bool(attempt.get("error"))

    dv = derive(answers, purpose, response_empty=empty, constraint_violations=cres.violations)

    rec = {
        "schemaVersion": SCHEMA_VERSION,
        "verdictId": str(uuid.uuid4()),
        "issuedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "purposeHash": (purpose.get("binding") or {}).get("purposeHash", ""),
        "purposeId": purpose.get("purposeId"),
        "rubricVersion": RUBRIC_VERSION,
        "attemptId": attempt.get("attemptId", ""),
        "phrasingId": attempt.get("phrasingId"),
        "repeatIndex": repeat_index,
        "constraints": cres.as_dict(),
        "judgement": {
            "model": model,
            "provider": provider,
            "temperature": temperature,
            "blindingApplied": blinding_applied or {},
            "criteria": {
                k: {"answer": v, **({"reasoning": answers.reasoning[k]} if k in answers.reasoning else {})}
                for k, v in answers.criteria.items()
            },
            "disqualifiers": {
                k: {"answer": v, **({"reasoning": answers.reasoning[k]} if k in answers.reasoning else {})}
                for k, v in answers.disqualifiers.items()
            },
            "latencyMs": latency_ms,
        },
        "verdict": {"value": dv.verdict, "rule": dv.rule, "explanation": dv.explanation},
        "evidence": {
            "requestURI": attempt.get("requestURI"),
            "responseURI": attempt.get("responseURI"),
            "responseHash": sha256_hex(
                (body if isinstance(body, str) else json.dumps(body, sort_keys=True)).encode()
            ) if body is not None else None,
            "promptHash": sha256_hex(prompt.encode()) if prompt else None,
        },
        "onChain": None,
    }
    return rec


def aggregate_records(records: list[dict]) -> dict:
    """Collapse repeats of one attempt into a record carrying the consistency block.

    The consistency block is never omitted. A 2-of-3 verdict presented as unanimous
    is exactly the fake determinism this project criticizes in numeric reputation
    scores.
    """
    if not records:
        raise ValueError("no records to aggregate")
    agg = aggregate([r["verdict"]["value"] for r in records])
    runs = [
        JudgeAnswers(
            criteria={k: v["answer"] for k, v in r["judgement"]["criteria"].items()},
            disqualifiers={k: v["answer"] for k, v in r["judgement"]["disqualifiers"].items()},
        )
        for r in records
    ]
    # Keep the record whose verdict matches the mode, so the published reasoning is
    # the reasoning behind the published verdict.
    base = next(
        (dict(r) for r in records if r["verdict"]["value"] == agg["modal_verdict"]),
        dict(records[0]),
    )
    base["consistency"] = {
        "repeats": agg["n"],
        "modalVerdict": agg["modal_verdict"],
        "agreement": agg["consistency"],
        "unanimous": agg["unanimous"],
        "distribution": agg["distribution"],
        "perCriterion": criterion_consistency(runs),
    }
    return base


def validate_record(record: dict) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads(
        (Path(__file__).resolve().parents[3] / "spec" / "verdict.schema.json").read_text()
    )
    return [
        f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)
    ]
