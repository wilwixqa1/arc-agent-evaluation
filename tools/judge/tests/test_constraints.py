"""Tests for the deterministic constraint checker and verdict record assembly."""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judgelib import (check_constraints, lookup, build_record, aggregate_records,
                      validate_record, verdict_hash, JudgeAnswers)

EX = Path(__file__).resolve().parents[3] / "spec" / "examples"
P01 = json.loads((EX / "p01-usdc-supply-lookup.json").read_text())
FX = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "p01.json").read_text())
GOOD = FX[0]["response"]
fails = []

def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond: fails.append(name)

def st(res, name):
    return next(c.status for c in res.checks if c.constraint == name)

def attempt(**kw):
    base = {"attemptId": "a", "body": copy.deepcopy(GOOD), "latencyMs": 1200, "pricePaidUsdc": 0.01}
    base.update(kw); return base

print("path lookup")
obj = {"a": {"b": [{"c": 7}]}, "x~y": 1}
check("dotted path", lookup(obj, "a.b[0].c") == 7)
check("json pointer", lookup(obj, "/a/b/0/c") == 7)
check("pointer escapes", lookup(obj, "/x~0y") == 1)
check("missing is not None", lookup(obj, "a.zzz") is not None and lookup(obj, "a.zzz") != 7)

print("\nchecks")
r = check_constraints(P01, attempt())
check("clean response has no violations", r.ok, str(r.violations))
check("unset constraint is not_applicable not pass",
      st(check_constraints({"constraints": {}}, attempt()), "maxPriceUsdc") == "not_applicable")
check("over price fails", "maxPriceUsdc" in check_constraints(P01, attempt(pricePaidUsdc=0.5)).violations)
check("at exact ceiling passes", check_constraints(P01, attempt(pricePaidUsdc=0.02)).ok)
check("over latency fails", "maxLatencyMs" in check_constraints(P01, attempt(latencyMs=99999)).violations)
check("unrecorded price is indeterminate not fail",
      st(check_constraints(P01, attempt(pricePaidUsdc=None)), "maxPriceUsdc") == "indeterminate")
check("indeterminate is not a violation",
      "maxPriceUsdc" not in check_constraints(P01, attempt(pricePaidUsdc=None)).violations)

b = copy.deepcopy(GOOD); del b["blockNumber"]
r = check_constraints(P01, attempt(body=b))
check("missing required field fails", "requiredFields" in r.violations)
check("missing field also trips its numeric bound", "numericBounds[blockNumber]" in r.violations)

b = copy.deepcopy(GOOD); b["blockNumber"] = None
check("null required field counts as missing",
      "requiredFields" in check_constraints(P01, attempt(body=b)).violations)
b = copy.deepcopy(GOOD); b["blockNumber"] = ""
check("empty string required field counts as missing",
      "requiredFields" in check_constraints(P01, attempt(body=b)).violations)

b = copy.deepcopy(GOOD); b["blockNumber"] = 12
check("below-min numeric bound fails",
      "numericBounds[blockNumber]" in check_constraints(P01, attempt(body=b)).violations)
b = copy.deepcopy(GOOD); b["totalSupply"] = "48221930114"
check("numeric string is accepted", check_constraints(P01, attempt(body=b)).ok)
b = copy.deepcopy(GOOD); b["totalSupply"] = "not a number"
check("non-numeric value fails its bound",
      "numericBounds[totalSupply]" in check_constraints(P01, attempt(body=b)).violations)

b = copy.deepcopy(GOOD); b["contract"] = "0xdeadbeef"
check("missing required substring fails",
      "requiredSubstrings" in check_constraints(P01, attempt(body=b)).violations)
check("substring match is case-insensitive",
      check_constraints(P01, attempt(body={**GOOD, "contract": GOOD["contract"].upper()})).ok)

check("text body against json format fails",
      "responseFormat" in check_constraints(P01, attempt(body="plain text")).violations)
check("json-encoded string body passes json format",
      "responseFormat" not in check_constraints(P01, attempt(body=json.dumps(GOOD))).violations)

check("freshness with no age reference is indeterminate",
      st(check_constraints(P01, attempt()), "freshness") == "indeterminate")
check("freshness fails when age exceeds the cap",
      "freshness" in check_constraints(P01, attempt(asOfAgeSeconds=9999)).violations)
check("freshness passes inside the cap",
      st(check_constraints(P01, attempt(asOfAgeSeconds=30)), "freshness") == "pass")

print("\nrecord assembly")
allmet = JudgeAnswers(criteria={"s1": "met", "s2": "met", "s3": "met", "s4": "met"},
                      disqualifiers={"d1": "not_triggered", "d2": "not_triggered", "d3": "not_triggered"})
rec = build_record(P01, attempt(), allmet, provider="p", model="m", prompt="x")
check("clean record is served", rec["verdict"]["value"] == "served", str(rec["verdict"]))
check("record validates against schema", not validate_record(rec), str(validate_record(rec)[:2]))
check("evidence carries a response hash", rec["evidence"]["responseHash"].startswith("0x"))
check("evidence carries a prompt hash", rec["evidence"]["promptHash"].startswith("0x"))
check("purposeHash is carried from the sealed purpose",
      rec["purposeHash"] == P01["binding"]["purposeHash"])

bad = build_record(P01, attempt(latencyMs=99999, pricePaidUsdc=0.9), allmet, prompt="x")
check("constraints override an all-met judgement",
      bad["verdict"]["value"] == "constraint_violated" and bad["verdict"]["rule"] == 2)
check("violations are named in the record",
      set(bad["constraints"]["violations"]) == {"maxPriceUsdc", "maxLatencyMs"})

empty = build_record(P01, attempt(body=None), allmet, prompt="x")
check("empty body is no_response", empty["verdict"]["value"] == "no_response")

print("\nverdict hashing")
h = verdict_hash(rec)
r2 = dict(rec); r2["onChain"] = {"chainId": 5042002, "field": "reason", "jobId": 7}
check("hash excludes onChain so writing it does not change it", verdict_hash(r2) == h)
r3 = copy.deepcopy(rec); r3["verdict"]["value"] = "not_served"
check("tampering with the verdict changes the hash", verdict_hash(r3) != h)
check("hash is 32 bytes", len(h) == 66)

print("\naggregation across repeats")
recs = [build_record(P01, attempt(), allmet, prompt="x") for _ in range(2)]
mixed = JudgeAnswers(criteria={"s1": "met", "s2": "met", "s3": "not_met", "s4": "met"},
                     disqualifiers={"d1": "not_triggered", "d2": "not_triggered", "d3": "not_triggered"})
recs.append(build_record(P01, attempt(), mixed, prompt="x"))
agg = aggregate_records(recs)
check("modal verdict is the majority", agg["consistency"]["modalVerdict"] == "served")
check("agreement is reported", agg["consistency"]["agreement"] == 0.667, str(agg["consistency"]))
check("non-unanimity is flagged", agg["consistency"]["unanimous"] is False)
check("disagreement localizes to the wobbling criterion",
      agg["consistency"]["perCriterion"]["s3"]["consistency"] == 0.667)
check("stable criterion reports full agreement",
      agg["consistency"]["perCriterion"]["s1"]["consistency"] == 1.0)
check("published reasoning matches the published verdict",
      agg["verdict"]["value"] == agg["consistency"]["modalVerdict"])
check("aggregated record still validates", not validate_record(agg), str(validate_record(agg)[:2]))

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
