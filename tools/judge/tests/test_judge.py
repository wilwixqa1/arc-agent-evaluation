"""Tests for everything in the judge path that does not require a provider key."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judgelib import (JudgeAnswers, derive, aggregate, criterion_consistency,
                      build_prompt, parse_judge_output, blind_attempt, scrub_text, SYSTEM)

EX = Path(__file__).resolve().parents[3] / "spec" / "examples"
P01 = json.loads((EX / "p01-usdc-supply-lookup.json").read_text())
fails = []

def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond: fails.append(name)

def ans(crit=None, disq=None):
    return JudgeAnswers(criteria=crit or {}, disqualifiers=disq or {})

allmet = {"s1": "met", "s2": "met", "s3": "met", "s4": "met"}
nodisq = {"d1": "not_triggered", "d2": "not_triggered", "d3": "not_triggered"}

print("verdict derivation (rule order)")
check("empty response -> no_response (rule 1)",
      derive(ans(allmet, nodisq), P01, response_empty=True).verdict == "no_response")
check("constraint violation outranks a perfect judge result (rule 2)",
      derive(ans(allmet, nodisq), P01, constraint_violations=["maxLatencyMs"]).verdict
      == "constraint_violated")
check("disqualifier outranks all criteria met (rule 3)",
      derive(ans(allmet, {**nodisq, "d1": "triggered"}), P01).verdict == "not_served")
check("no criterion met -> not_served (rule 4)",
      derive(ans({k: "not_met" for k in allmet}, nodisq), P01).verdict == "not_served")
check("necessary criterion not_met caps at partially_served (rule 5)",
      derive(ans({**allmet, "s1": "not_met"}, nodisq), P01).verdict == "partially_served")
check("necessary criterion unclear also caps, does not pass (rule 5)",
      derive(ans({**allmet, "s2": "unclear"}, nodisq), P01).verdict == "partially_served")
check("non-necessary criterion not_met -> partially_served (rule 7)",
      derive(ans({**allmet, "s3": "not_met"}, nodisq), P01).verdict == "partially_served")
check("all met, none triggered -> served (rule 6)",
      derive(ans(allmet, nodisq), P01).verdict == "served")
check("rule number is reported",
      derive(ans(allmet, nodisq), P01).rule == 6)
check("derivation is deterministic",
      derive(ans(allmet, nodisq), P01).verdict == derive(ans(allmet, nodisq), P01).verdict)

print("\naggregation")
a = aggregate(["served", "served", "partially_served"])
check("modal verdict wins", a["modal_verdict"] == "served")
check("consistency reported as a fraction", a["consistency"] == 0.667, str(a))
check("non-unanimous is flagged", a["unanimous"] is False)
check("unanimous is flagged", aggregate(["served"] * 3)["unanimous"] is True)
check("empty aggregate does not crash", aggregate([])["modal_verdict"] is None)

cc = criterion_consistency([ans({"s1": "met", "s2": "met"}),
                            ans({"s1": "met", "s2": "not_met"}),
                            ans({"s1": "met", "s2": "met"})])
check("stable criterion reports 1.0", cc["s1"]["consistency"] == 1.0)
check("wobbling criterion is localized", cc["s2"]["consistency"] == 0.667, str(cc["s2"]))

print("\nblinding")
attempt = {"provider": "AcmeAPI", "priceUsdc": 0.02, "phrasingId": "v3",
           "meta": {"endpoint": "https://acme.example/x", "latencyMs": 900},
           "body": {"totalSupply": "1"}}
bl = {"hideProvider": True, "hidePrice": True, "hidePhrasingId": True}
red, removed = blind_attempt(attempt, bl)
check("provider removed", "provider" not in red)
check("price removed", "priceUsdc" not in red)
check("phrasing removed", "phrasingId" not in red)
check("nested endpoint removed", "endpoint" not in red["meta"])
check("non-blinded nested field kept", red["meta"]["latencyMs"] == 900)
check("body preserved", red["body"]["totalSupply"] == "1")
check("removals are reported", set(removed) >= {"provider", "priceUsdc", "phrasingId", "endpoint"})
check("original not mutated", attempt["provider"] == "AcmeAPI")
kept, _ = blind_attempt(attempt, {"hideProvider": False, "hidePrice": False, "hidePhrasingId": False})
check("blinding off keeps everything", kept["provider"] == "AcmeAPI" and "priceUsdc" in kept)
check("in-body provider name scrubbed",
      "acme" not in scrub_text("Powered by AcmeAPI v2", ["AcmeAPI"]).lower())

print("\nprompt assembly")
p = build_prompt(P01, {"totalSupply": "1"})
check("every success criterion appears", all(c["id"] in p for c in P01["objective"]["successCriteria"]))
check("every disqualifier appears", all(d["id"] in p for d in P01["objective"]["disqualifiers"]))
check("goal included", P01["objective"]["goal"][:40] in p)
check("out of scope included", "Explicitly not required" in p)
check("response delimited", "<<<RESPONSE" in p and "RESPONSE>>>" in p)
check("prompt does not leak the derivation rule",
      not any(t in p.lower() for t in ["partially_served", "verdict", "rule 1"]))
check("system prompt forbids an overall verdict",
      "not produce an overall verdict" in SYSTEM)
check("system prompt offers unclear as a real answer", "unclear is a real answer" in SYSTEM)

print("\noutput parsing")
good = '{"criteria":{"s1":{"answer":"met","reasoning":"x"}},"disqualifiers":{}}'
check("plain json parses", parse_judge_output(good)["criteria"]["s1"]["answer"] == "met")
check("code fence tolerated", parse_judge_output(f"```json\n{good}\n```")["criteria"]["s1"]["answer"] == "met")
check("leading prose tolerated", parse_judge_output(f"Here you go:\n{good}")["criteria"]["s1"]["answer"] == "met")
try:
    parse_judge_output("no json here at all"); check("garbage raises", False)
except ValueError:
    check("garbage raises", True)

print("\nfixtures")
fixdir = Path(__file__).resolve().parents[1] / "fixtures"
fixtures = [f for p in sorted(fixdir.glob("*.json")) for f in json.loads(p.read_text())]
purposes = {p.name for p in EX.glob("*.json")}
check("24 fixtures", len(fixtures) == 24, str(len(fixtures)))
check("ids unique", len({f["fixtureId"] for f in fixtures}) == 24)
check("every fixture resolves to a purpose", all(f["purposeFile"] in purposes for f in fixtures))
check("clear fixtures carry an expected verdict",
      all(f["expectedVerdict"] for f in fixtures if f["label"] != "ambiguous"))
check("ambiguous fixtures carry no expected verdict",
      all(f["expectedVerdict"] is None for f in fixtures if f["label"] == "ambiguous"))
check("every fixture states a labeller rationale",
      all(len(f["labellerRationale"]) > 30 for f in fixtures))
check("at least one clear-served exists", any(f["label"] == "clear-served" for f in fixtures))
check("expected disqualifiers exist in their purpose",
      all(d in {x["id"] for x in json.loads((EX / f["purposeFile"]).read_text())["objective"]["disqualifiers"]}
          for f in fixtures for d in f["expectedDisqualifiers"]))

print("\nend to end, no provider")
for f in fixtures[:6]:
    pur = json.loads((EX / f["purposeFile"]).read_text())
    pr = build_prompt(pur, f["response"])
    if not (len(pr) > 200): check(f"{f['fixtureId']} prompt built", False)
check("prompts build for a sample of fixtures", True)

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
