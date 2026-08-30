#!/usr/bin/env python3
"""Phase 0: does the judge agree with itself, and with a human, on known fixtures?

This is the gate. Everything downstream assumes an LLM can grade purpose satisfaction
reliably, and that assumption is untested until this runs. No blockchain involved, no
services called, no wallet needed.

    export ANTHROPIC_API_KEY=...       # or OPENAI_API_KEY / GOOGLE_API_KEY
    export JUDGE_PROVIDER=anthropic
    python run_phase0.py --repeats 3

    python run_phase0.py --dry-run     # assemble prompts, call nothing

Exit criteria (spec/rubric/v0.1.0.md §5), measured on clear fixtures only:
    self-consistency  >= 90%
    human agreement   >= 80%

Ambiguous fixtures are excluded from both and are not failures. A judge that is
confidently decisive on a genuinely ambiguous case is worse than one that wavers.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from judgelib import (  # noqa: E402
    JudgeAnswers, SYSTEM, aggregate, available_providers, build_prompt, build_record,
    criterion_consistency, derive, get_provider, parse_judge_output, validate_record,
    RUBRIC_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "spec" / "examples"
FIXTURES = Path(__file__).parent / "fixtures"
OUT = Path(__file__).parent / "results"

SELF_CONSISTENCY_BAR = 0.90
HUMAN_AGREEMENT_BAR = 0.80


def load_all() -> list[dict]:
    purposes = {p.name: json.loads(p.read_text()) for p in EXAMPLES.glob("*.json")}
    items = []
    for f in sorted(FIXTURES.glob("*.json")):
        for fix in json.loads(f.read_text()):
            purpose = purposes.get(fix["purposeFile"])
            if purpose is None:
                raise SystemExit(f"{fix['fixtureId']}: no purpose {fix['purposeFile']}")
            items.append({"fixture": fix, "purpose": purpose})
    return items


def to_answers(parsed: dict) -> JudgeAnswers:
    ans = JudgeAnswers(raw=parsed)
    for cid, v in (parsed.get("criteria") or {}).items():
        ans.criteria[cid] = v["answer"] if isinstance(v, dict) else v
        if isinstance(v, dict) and v.get("reasoning"):
            ans.reasoning[cid] = v["reasoning"]
    for did, v in (parsed.get("disqualifiers") or {}).items():
        ans.disqualifiers[did] = v["answer"] if isinstance(v, dict) else v
        if isinstance(v, dict) and v.get("reasoning"):
            ans.reasoning[did] = v["reasoning"]
    return ans


def run(items: list[dict], repeats: int, provider, dry_run: bool, seed: int) -> list[dict]:
    # Shuffle so the judge never sees a purpose-grouped batch. Blinding without
    # shuffling leaks the grouping through ordering.
    order = list(range(len(items)))
    random.Random(seed).shuffle(order)

    results: dict[str, dict] = {}
    total = len(order) * repeats
    done = 0

    for rep in range(repeats):
        for idx in order:
            item = items[idx]
            fix, purpose = item["fixture"], item["purpose"]
            fid = fix["fixtureId"]
            prompt = build_prompt(purpose, fix["response"])
            rec = results.setdefault(fid, {
                "fixtureId": fid,
                "purposeFile": fix["purposeFile"],
                "label": fix["label"],
                "expectedVerdict": fix["expectedVerdict"],
                "expectedDisqualifiers": fix["expectedDisqualifiers"],
                "runs": [],
                "prompt_chars": len(prompt),
            })
            done += 1
            if dry_run:
                continue
            try:
                comp = provider.complete(SYSTEM, prompt)
                ans = to_answers(parse_judge_output(comp.text))
                # Fixtures carry no observed latency or price, so the constraint pass
                # returns not_applicable or indeterminate throughout. It runs anyway,
                # so the same code path is exercised here as on a real attempt.
                vrec = build_record(
                    purpose,
                    {"attemptId": fid, "body": fix["response"]},
                    ans,
                    provider=comp.provider, model=comp.model,
                    blinding_applied=(purpose.get("evaluation") or {}).get("blinding", {}),
                    latency_ms=comp.latency_ms, repeat_index=rep, prompt=prompt,
                )
                schema_errs = validate_record(vrec)
                dv_verdict, dv_rule = vrec["verdict"]["value"], vrec["verdict"]["rule"]
                rec.setdefault("verdictRecords", []).append(vrec)
                rec["runs"].append({
                    "repeat": rep,
                    "verdict": dv_verdict,
                    "rule": dv_rule,
                    "explanation": vrec["verdict"]["explanation"],
                    "schema_errors": schema_errs,
                    "criteria": ans.criteria,
                    "disqualifiers": ans.disqualifiers,
                    "reasoning": ans.reasoning,
                    "latency_ms": comp.latency_ms,
                    "model": comp.model,
                })
            except Exception as exc:
                rec["runs"].append({"repeat": rep, "error": f"{type(exc).__name__}: {exc}"})
            print(f"  [{done}/{total}] {fid} rep{rep} "
                  f"-> {rec['runs'][-1].get('verdict', rec['runs'][-1].get('error'))}", flush=True)
            time.sleep(0.2)
    return list(results.values())


def score(records: list[dict]) -> dict:
    for r in records:
        good = [x for x in r["runs"] if "verdict" in x]
        r["aggregate"] = aggregate([x["verdict"] for x in good])
        r["criterion_consistency"] = criterion_consistency(
            [JudgeAnswers(criteria=x["criteria"], disqualifiers=x["disqualifiers"])
             for x in good]
        )
        r["errors"] = len(r["runs"]) - len(good)
        if r["expectedVerdict"] and r["aggregate"]["modal_verdict"]:
            r["matches_human"] = r["aggregate"]["modal_verdict"] == r["expectedVerdict"]
        else:
            r["matches_human"] = None

    clear = [r for r in records if r["label"] != "ambiguous" and r["aggregate"]["n"]]
    amb = [r for r in records if r["label"] == "ambiguous" and r["aggregate"]["n"]]

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else 0.0

    sc = mean([r["aggregate"]["consistency"] for r in clear])
    ha = mean([1.0 if r["matches_human"] else 0.0 for r in clear if r["matches_human"] is not None])

    crit_all = [c["consistency"] for r in records for c in r["criterion_consistency"].values()]

    return {
        "rubricVersion": RUBRIC_VERSION,
        "fixtures_total": len(records),
        "fixtures_clear": len(clear),
        "fixtures_ambiguous": len(amb),
        "self_consistency_clear": sc,
        "self_consistency_ambiguous": mean([r["aggregate"]["consistency"] for r in amb]),
        "human_agreement_clear": ha,
        "criterion_level_consistency": mean(crit_all),
        "unanimous_clear": sum(1 for r in clear if r["aggregate"]["unanimous"]),
        "run_errors": sum(r["errors"] for r in records),
        "bars": {
            "self_consistency": {"threshold": SELF_CONSISTENCY_BAR, "value": sc,
                                 "pass": sc >= SELF_CONSISTENCY_BAR},
            "human_agreement": {"threshold": HUMAN_AGREEMENT_BAR, "value": ha,
                                "pass": ha >= HUMAN_AGREEMENT_BAR},
        },
        "verdict_distribution_clear": dict(Counter(
            r["aggregate"]["modal_verdict"] for r in clear)),
        "verdict_distribution_ambiguous": dict(Counter(
            r["aggregate"]["modal_verdict"] for r in amb)),
        "disagreements": [
            {"fixtureId": r["fixtureId"], "expected": r["expectedVerdict"],
             "got": r["aggregate"]["modal_verdict"], "consistency": r["aggregate"]["consistency"]}
            for r in clear if r["matches_human"] is False
        ],
        "lowest_consistency_criteria": sorted(
            [{"fixtureId": r["fixtureId"], "item": k, **v}
             for r in records for k, v in r["criterion_consistency"].items()],
            key=lambda x: x["consistency"],
        )[:10],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--dry-run", action="store_true", dest="dry_run")
    args = ap.parse_args()

    items = load_all()
    print(f"{len(items)} fixtures, {args.repeats} repeats, rubric v{RUBRIC_VERSION}")

    provider = None
    if not args.dry_run:
        keys = available_providers()
        if not keys:
            print("\nNo provider key found. Set one of ANTHROPIC_API_KEY, OPENAI_API_KEY, "
                  "GOOGLE_API_KEY, or pass --dry-run to assemble prompts without calling out.")
            raise SystemExit(2)
        provider = get_provider(args.provider, args.model)
        if not provider.available():
            print(f"\nNo key for provider {provider.name!r}. Keys present: {keys}")
            raise SystemExit(2)
        print(f"provider {provider.name} model {provider.model}\n")

    records = run(items, args.repeats, provider, args.dry_run, args.seed)

    if args.dry_run:
        sizes = [r["prompt_chars"] for r in records]
        print(f"\nDry run. {len(records)} prompts assembled.")
        print(f"  prompt size min {min(sizes)} / mean {sum(sizes)//len(sizes)} / max {max(sizes)} chars")
        print(f"  calls a real run would make: {len(records) * args.repeats}")
        print("  no provider contacted")
        return

    summary = score(records)
    OUT.mkdir(exist_ok=True)
    (OUT / "phase0_records.json").write_text(json.dumps(records, indent=2))
    verdicts = [v for r in records for v in r.get("verdictRecords", [])]
    (OUT / "verdict_records.json").write_text(json.dumps(verdicts, indent=2))
    summary["verdict_records_written"] = len(verdicts)
    summary["verdict_schema_errors"] = sum(
        1 for r in records for x in r["runs"] if x.get("schema_errors"))
    (OUT / "phase0_summary.json").write_text(json.dumps(summary, indent=2))

    print("\n" + json.dumps(summary, indent=2))
    bars = summary["bars"]
    ok = bars["self_consistency"]["pass"] and bars["human_agreement"]["pass"]
    print("\n" + ("PHASE 0 PASSED" if ok else "PHASE 0 FAILED: fix the rubric or change "
                                              "the model, do not lower the bar"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
