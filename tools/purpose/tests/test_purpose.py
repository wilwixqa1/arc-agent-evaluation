"""Property tests for purpose sealing, validation and specificity."""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from purposelib import canonicalize, purpose_hash, seal, verify_seal, validate, specificity

EX = Path(__file__).resolve().parents[3] / "spec" / "examples"
STRONG = json.loads((EX / "p01-usdc-supply-lookup.json").read_text())
WEAK = json.loads((EX / "p04-WEAK-negative-fixture.json").read_text())

failures = []

def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        failures.append(name)

print("canonicalization")
check("keys sort by UTF-16 code unit",
      canonicalize({"b": 1, "A": 2}) == b'{"A":2,"b":1}')
check("floats with integral value lose the decimal point",
      canonicalize({"x": 3.0}) == b'{"x":3}')
check("no insignificant whitespace",
      b" " not in canonicalize({"a": [1, 2], "b": {"c": 3}}))

print("\nsealing")
h1 = purpose_hash(STRONG)
reordered = dict(reversed(list(STRONG.items())))
check("hash is stable under key reordering", purpose_hash(reordered) == h1)
roundtripped = json.loads(json.dumps(STRONG, indent=7))
check("hash is stable under reformatting", purpose_hash(roundtripped) == h1)

sealed = seal(STRONG, sealed_at="2026-08-30T12:00:00Z")
ok, val = verify_seal(sealed)
check("seal then verify round-trips", ok and val == h1)

with_chain = seal(STRONG, on_chain={"chainId": 5042002, "field": "description", "jobId": 42})
check("hash is unchanged by later on-chain metadata",
      with_chain["binding"]["purposeHash"] == h1)

tampered = copy.deepcopy(sealed)
tampered["objective"]["successCriteria"][0]["statement"] = "anything at all goes here"
ok2, msg = verify_seal(tampered)
check("tampering with a criterion breaks the seal", not ok2, msg)

tampered2 = copy.deepcopy(sealed)
tampered2["constraints"]["maxPriceUsdc"] = 99.0
check("tampering with a constraint breaks the seal", not verify_seal(tampered2)[0])

print("\nvalidation")
check("strong example validates", validate(STRONG).ok)
check("weak example is still structurally valid", validate(WEAK).ok,
      "vagueness is measured, not rejected")
check("weak example raises warnings", len(validate(WEAK).warnings) >= 3)

dup = copy.deepcopy(STRONG)
dup["objective"]["successCriteria"][1]["id"] = "s1"
check("duplicate criterion ids rejected", not validate(dup).ok)

restate = copy.deepcopy(STRONG)
restate["objective"]["successCriteria"][0]["statement"] = restate["task"]["summary"]
check("criterion restating task.summary rejected", not validate(restate).ok)

nodisq = copy.deepcopy(STRONG)
nodisq["objective"]["disqualifiers"] = []
check("empty disqualifiers rejected by schema", not validate(nodisq).ok)

onecrit = copy.deepcopy(STRONG)
onecrit["objective"]["successCriteria"] = onecrit["objective"]["successCriteria"][:1]
check("single success criterion rejected by schema", not validate(onecrit).ok)

extra = copy.deepcopy(STRONG)
extra["objective"]["notes"] = "smuggled field"
check("unknown fields rejected", not validate(extra).ok)

print("\nspecificity")
s_strong, s_weak = specificity(STRONG).score, specificity(WEAK).score
check("strong scores above 0.7", s_strong > 0.7, f"got {s_strong}")
check("weak scores below 0.3", s_weak < 0.3, f"got {s_weak}")
check("separation exceeds 0.5", s_strong - s_weak > 0.5, f"gap {round(s_strong-s_weak,3)}")

stripped = copy.deepcopy(STRONG)
stripped["objective"]["disqualifiers"] = stripped["objective"]["disqualifiers"][:1]
check("removing disqualifiers lowers the score",
      specificity(stripped).score < s_strong)

vague = copy.deepcopy(STRONG)
for c in vague["objective"]["successCriteria"]:
    c["statement"] = "The response is appropriate and of good quality for the request."
check("replacing criteria with hedges lowers the score",
      specificity(vague).score < s_strong)

check("specificity is outcome-independent",
      specificity(STRONG).score == specificity(copy.deepcopy(STRONG)).score)

print(f"\n{'ALL PASS' if not failures else str(len(failures)) + ' FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
