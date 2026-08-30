"""Tests for the calibration services. No network, no keys: the handler logic is
exercised directly and the HTTP layer separately."""
import json, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "judge"))
from http.server import ThreadingHTTPServer
import services
from services import serve_one, PROFILES, RESOURCES, TRUTH, seeded, BRITTLE_PATTERNS
from phrasings import PHRASINGS
from client import fetch
from judgelib import check_constraints

fails = []
def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond: fails.append(name)

CANON = PHRASINGS["usdc-supply"][0]["text"]
PARA = PHRASINGS["usdc-supply"][1]["text"]

print("determinism")
check("same attempt gives the same behaviour",
      serve_one("flaky", "usdc-supply", CANON, "a1").note ==
      serve_one("flaky", "usdc-supply", CANON, "a1").note)
check("different attempts can differ",
      len({serve_one("flaky", "usdc-supply", CANON, f"a{i}").status for i in range(30)}) > 1)
check("seeding is stable across processes",
      seeded("flaky", "a1").random() == seeded("flaky", "a1").random())

print("\nprofiles")
check("honest returns the truth",
      serve_one("honest", "usdc-supply", CANON, "x").body == TRUTH["usdc-supply"])
check("deadbeat returns 200 with an empty body",
      serve_one("deadbeat", "usdc-supply", CANON, "x").body == {} and
      serve_one("deadbeat", "usdc-supply", CANON, "x").status == 200)
tr = serve_one("truncator", "usdc-supply", CANON, "x").body
check("truncator drops provenance", "blockNumber" not in tr and "source" not in tr)
check("truncator keeps a plausible shape", "totalSupply" in tr and "contract" in tr)

print("\nbrittle is phrasing-dependent, not liveness-dependent")
c = serve_one("brittle", "usdc-supply", CANON, "x")
p = serve_one("brittle", "usdc-supply", PARA, "x")
check("canonical phrasing succeeds", c.body == TRUTH["usdc-supply"])
check("paraphrase degrades", p.body != TRUTH["usdc-supply"])
check("both return HTTP 200", c.status == 200 and p.status == 200,
      "an uptime monitor cannot distinguish these")
for r in RESOURCES:
    hits = [x["phrasingId"] for x in PHRASINGS[r] if BRITTLE_PATTERNS[r].search(x["text"])]
    check(f"{r}: brittle matches some but not all phrasings",
          0 < len(hits) < len(PHRASINGS[r]), str(hits))

print("\nconfabulator")
notes = [serve_one("confabulator", "usdc-supply", CANON, f"a{i}").note for i in range(40)]
fab = sum(1 for n in notes if "FABRICATED" in n)
check("fabricates a meaningful share of the time", 8 < fab < 32, f"{fab}/40")
bodies = [serve_one("confabulator", "usdc-supply", CANON, f"a{i}").body for i in range(40)]
check("shape is identical whether fabricating or not",
      len({tuple(sorted(b)) for b in bodies}) == 1)

print("\nflaky")
st = [serve_one("flaky", "usdc-supply", CANON, f"a{i}").status for i in range(100)]
rate = st.count(200) / 100
check("success rate is near the configured 0.70", 0.55 < rate < 0.85, f"{rate}")

print("\nhttp and x402 envelope")
srv = ThreadingHTTPServer(("127.0.0.1", 8451), services.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.3)
try:
    a = fetch("http://127.0.0.1:8451", "honest", "usdc-supply", CANON, "t1")
    check("payment required then resource returned", a.status == 200 and a.body is not None)
    check("402 envelope was parsed", a.paymentRequired is not None)
    check("price recorded from the envelope", a.pricePaidUsdc == 0.01, str(a.pricePaidUsdc))
    check("latency recorded", isinstance(a.latencyMs, int))
    check("ground truth captured out of band", "note" in a.groundTruth)
    check("judge view hides ground truth", "groundTruth" not in a.for_judge())
    check("judge view hides profile identity", "profile" not in a.for_judge())
    d = fetch("http://127.0.0.1:8451", "deadbeat", "usdc-supply", CANON, "t2")
    check("deadbeat still charges", d.pricePaidUsdc == 0.01 and d.body == {})
finally:
    srv.shutdown()

print("\nconstraint separation")
P = json.loads((Path(__file__).resolve().parents[3] / "spec" / "examples" /
                "p01-usdc-supply-lookup.json").read_text())
def att(profile, q, aid):
    r = serve_one(profile, "usdc-supply", q, aid)
    return {"attemptId": aid, "body": r.body if r.status == 200 else None,
            "latencyMs": 100, "pricePaidUsdc": 0.01}
check("honest passes every hard constraint", check_constraints(P, att("honest", CANON, "c1")).ok)
check("truncator is caught by constraints alone",
      not check_constraints(P, att("truncator", CANON, "c2")).ok)
check("brittle paraphrase is caught by constraints alone",
      not check_constraints(P, att("brittle", PARA, "c3")).ok)
check("confabulator passes every hard constraint",
      check_constraints(P, att("confabulator", CANON, "c4")).ok,
      "by design: only content evaluation can catch it")

print("\nmanifest")
m = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())
check("every profile is documented", set(m["profiles"]) == set(PROFILES))
check("every profile states a rationale",
      all(len(v["rationale"]) > 30 for v in m["profiles"].values()))
check("every resource carries its truth", set(m["resources"]) == set(RESOURCES))

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
