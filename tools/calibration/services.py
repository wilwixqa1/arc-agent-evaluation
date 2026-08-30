"""Calibration services: six x402 sellers with deliberately engineered quality profiles.

These exist so the evaluator can be tested against known ground truth. Consistency is
not correctness: a judge can be perfectly self-consistent and consistently wrong, and
the only way to tell the difference is to grade responses whose quality we already
know. That is measurement integrity, which arXiv:2108.05521 identifies as the thing
peer-prediction work usually ignores and the thing we actually care about.

They also seed the failure taxonomy with designed failures before we go looking for
real ones, and on Arc they are the only shoppable services that exist (0 of 250 sampled
agents had a reachable endpoint).

## The profiles

| id | Behaviour | What it tests |
|---|---|---|
| `honest` | Correct, complete, provenance included | Control. Anything that fails here is our bug. |
| `flaky` | Correct 70% of the time, errors otherwise, independent of phrasing | Variance that is NOT phrasing-driven |
| `brittle` | Correct only when the query matches an expected pattern; degrades badly on paraphrase | **The case for D3.** Uptime monitors see 100%; only paraphrase variance catches it |
| `deadbeat` | Takes payment, returns HTTP 200 with an empty body | "Paid and got nothing" |
| `truncator` | Well-formed but silently degraded: drops provenance, rounds figures, omits fields | Silent quality degradation, the hardest failure to see |
| `confabulator` | Always confident, always well-formed, content sometimes fabricated | Whether the judge distinguishes correct shape from correct content |

`brittle` is the important one. It is invisible to every tool in the competitive
landscape, because they all measure liveness and it is always live.

## Determinism

Behaviour is seeded on `(profile, attemptId)`. The same attempt always produces the
same response, so a rerun reproduces the dataset exactly, and variance across repeats
comes from the seed changing rather than from wall-clock randomness. Without this you
cannot separate service variance from judge variance, which is the whole point of the
repeats.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# --------------------------------------------------------------------------
# Ground truth: the correct answers these services are meant to be selling
# --------------------------------------------------------------------------

TRUTH = {
    "usdc-supply": {
        "contract": "0x3600000000000000000000000000000000000000",
        "chainId": 5042002,
        "totalSupply": "48221930114",
        "decimals": 6,
        "totalSupplyFormatted": "48221.930114 USDC",
        "blockNumber": 59445102,
        "source": "live eth_call",
    },
    "x402-summary": {
        "windowStart": "2026-08-29T12:00:00Z",
        "windowEnd": "2026-08-30T12:00:00Z",
        "protocol": "x402",
        "chain": "base",
        "transactionCount": 41277,
        "settledVolumeUsdc": 18944.22,
        "uniquePayers": 3120,
        "comparisonBaseline": "preceding 24h window 2026-08-28T12:00Z to 2026-08-29T12:00Z",
        "changeVsBaseline": "+7.4% by transaction count",
        "methodology": "filtered to transfers carrying an x402 facilitator settlement marker, excludes general USDC transfers",
    },
    "contract-analysis": {
        "address": "0x0747EEf0706327138c69792bF28Cd525089e4583",
        "isProxy": True,
        "proxyStandard": "ERC-1967 (UUPS)",
        "implementation": "0xa316fd02827242d537f84730f8a37d0ba5fd351a",
        "upgradeControl": "AccessControl, ADMIN_ROLE and DEFAULT_ADMIN_ROLE, via upgradeToAndCall",
        "adminMutableParameters": ["setEvaluatorFee", "setPlatformFee", "setHookWhitelist"],
        "evidence": "implementation slot 0x360894a1...382bbc is populated; ABI exposes proxiableUUID and grantRole",
        "uncertainty": "current ADMIN_ROLE holders not reviewed; would need RoleGranted history",
    },
}

RESOURCES = list(TRUTH)
PRICE_USDC = {"usdc-supply": 0.01, "x402-summary": 0.05, "contract-analysis": 0.20}

# Queries `brittle` recognizes. Anything else and it degrades. Chosen to be the
# literal phrasing of each purpose's task.summary, so any paraphrase misses.
BRITTLE_PATTERNS = {
    "usdc-supply": re.compile(r"\btotal\s+usdc\s+supply\b.*\barc\b", re.I),
    "x402-summary": re.compile(r"\bx402\b.*\b(24|twenty[- ]four)\s*hour", re.I),
    "contract-analysis": re.compile(r"\bwho\s+can\s+upgrade\b", re.I),
}

FLAKY_SUCCESS_RATE = 0.70


def seeded(profile: str, attempt_id: str) -> random.Random:
    """Deterministic per (profile, attempt). Same attempt, same behaviour, always."""
    h = hashlib.sha256(f"{profile}:{attempt_id}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


# --------------------------------------------------------------------------
# Profiles
# --------------------------------------------------------------------------

@dataclass
class Reply:
    status: int
    body: object
    note: str  # what the service did, for the manifest. Never sent to the judge.


def honest(resource: str, query: str, rng: random.Random) -> Reply:
    return Reply(200, dict(TRUTH[resource]), "correct and complete")


def flaky(resource: str, query: str, rng: random.Random) -> Reply:
    if rng.random() < FLAKY_SUCCESS_RATE:
        return Reply(200, dict(TRUTH[resource]), "correct (flaky roll succeeded)")
    return Reply(503, {"error": "upstream temporarily unavailable"},
                 "errored (flaky roll failed)")


def brittle(resource: str, query: str, rng: random.Random) -> Reply:
    """Correct only for the expected phrasing. Always live, so uptime monitoring
    cannot see this failure mode at all."""
    if BRITTLE_PATTERNS[resource].search(query or ""):
        return Reply(200, dict(TRUTH[resource]), "correct (query matched expected pattern)")
    generic = {
        "usdc-supply": {"answer": "USDC is a fully reserved dollar stablecoin issued by Circle. "
                                  "Supply figures vary by chain and can be read from the token contract."},
        "x402-summary": {"answer": "x402 is an HTTP-native payment protocol using the 402 status "
                                   "code. Activity levels depend on the chain and time period queried."},
        "contract-analysis": {"answer": "Smart contracts may be deployed behind proxies to allow "
                                        "upgrades. Access to upgrades is normally restricted."},
    }[resource]
    return Reply(200, generic, "degraded to generic non-answer (query did not match pattern)")


def deadbeat(resource: str, query: str, rng: random.Random) -> Reply:
    return Reply(200, {}, "took payment, returned nothing")


def truncator(resource: str, query: str, rng: random.Random) -> Reply:
    """Silently degraded. Well-formed, plausible, missing exactly the provenance that
    makes it usable. The hardest failure to notice and the one most likely to pass a
    schema check."""
    body = dict(TRUTH[resource])
    if resource == "usdc-supply":
        body.pop("blockNumber", None)
        body.pop("source", None)
        body.pop("decimals", None)
        body.pop("totalSupplyFormatted", None)
        body["totalSupply"] = "48222000000"  # rounded, no longer exact
        note = "dropped blockNumber, decimals and source; rounded totalSupply"
    elif resource == "x402-summary":
        for k in ("comparisonBaseline", "changeVsBaseline", "methodology", "uniquePayers"):
            body.pop(k, None)
        note = "dropped baseline, methodology and payer count"
    else:
        for k in ("evidence", "uncertainty", "adminMutableParameters", "implementation"):
            body.pop(k, None)
        note = "dropped evidence, uncertainty and mutable parameter list"
    return Reply(200, body, note)


def confabulator(resource: str, query: str, rng: random.Random) -> Reply:
    """Confident and well-formed. Roughly half the time the content is invented, and
    the shape is identical either way, so only content evaluation separates them."""
    if rng.random() < 0.5:
        return Reply(200, dict(TRUTH[resource]), "correct (confabulation roll passed)")
    fake = {
        "usdc-supply": {
            "contract": "0x3600000000000000000000000000000000000000", "chainId": 5042002,
            "totalSupply": "912774310558", "decimals": 6,
            "totalSupplyFormatted": "912774.310558 USDC", "blockNumber": 61002884,
            "source": "live eth_call"},
        "x402-summary": {
            "windowStart": "2026-08-29T12:00:00Z", "windowEnd": "2026-08-30T12:00:00Z",
            "protocol": "x402", "chain": "base", "transactionCount": 512904,
            "settledVolumeUsdc": 4410233.87, "uniquePayers": 48210,
            "comparisonBaseline": "preceding 24h window",
            "changeVsBaseline": "+212% by transaction count",
            "methodology": "aggregated from facilitator settlement events"},
        "contract-analysis": {
            "address": "0x0747EEf0706327138c69792bF28Cd525089e4583", "isProxy": True,
            "proxyStandard": "ERC-1967 (Transparent)",
            "implementation": "0x4d2c8f1b9a7e6c3d5f0a8b2e9c4d7f1a3b6e8c05",
            "upgradeControl": "GOVERNOR_ROLE via scheduleUpgrade with a 48-hour timelock",
            "adminMutableParameters": ["setProtocolConfig", "setTreasury"],
            "evidence": "verified on Arcscan",
            "uncertainty": "none"},
    }[resource]
    return Reply(200, fake, "FABRICATED content, correct shape (confabulation roll failed)")


PROFILES = {
    "honest": honest,
    "flaky": flaky,
    "brittle": brittle,
    "deadbeat": deadbeat,
    "truncator": truncator,
    "confabulator": confabulator,
}


def serve_one(profile: str, resource: str, query: str, attempt_id: str) -> Reply:
    if profile not in PROFILES:
        raise KeyError(profile)
    if resource not in TRUTH:
        raise KeyError(resource)
    return PROFILES[profile](resource, query, seeded(profile, attempt_id))


# --------------------------------------------------------------------------
# x402 envelope
# --------------------------------------------------------------------------

PAY_TO = "0x000000000000000000000000000000000000dEaD"
USDC = "0x3600000000000000000000000000000000000000"


def payment_required(resource: str, path: str) -> dict:
    """The 402 body. Shape follows the x402 `exact` scheme so a real client is
    exercised, but settlement is mocked: nothing is submitted on chain."""
    return {
        "x402Version": 1,
        "accepts": [{
            "scheme": "exact",
            "network": "arc-testnet",
            "maxAmountRequired": str(int(PRICE_USDC[resource] * 1_000_000)),
            "resource": path,
            "description": f"calibration service resource: {resource}",
            "mimeType": "application/json",
            "payTo": PAY_TO,
            "asset": USDC,
            "maxTimeoutSeconds": 60,
            "extra": {"name": "USDC", "version": "2", "decimals": 6},
        }],
        "error": "payment required",
    }


class Handler(BaseHTTPRequestHandler):
    require_payment = True

    def log_message(self, *a):  # quiet
        pass

    def _json(self, status: int, body, headers: dict | None = None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.strip("/").split("/") if p]
        if parts == ["_profiles"]:
            return self._json(200, {"profiles": list(PROFILES), "resources": RESOURCES,
                                    "prices": PRICE_USDC})
        if len(parts) != 2:
            return self._json(404, {"error": "expected /{profile}/{resource}"})
        profile, resource = parts
        if profile not in PROFILES or resource not in TRUTH:
            return self._json(404, {"error": "unknown profile or resource"})

        qs = parse_qs(u.query)
        query = (qs.get("q") or [""])[0]
        attempt_id = (qs.get("attemptId") or [""])[0] or f"anon-{time.time_ns()}"

        pay = self.headers.get("X-PAYMENT")
        if self.require_payment and not pay:
            return self._json(402, payment_required(resource, u.path))

        reply = serve_one(profile, resource, query, attempt_id)
        # The note describes what the service did. It is a debugging and manifest
        # aid and must never reach the judge, so it goes in a header the shopper
        # records out of band rather than in the body.
        self._json(reply.status, reply.body, {
            "X-PAYMENT-RESPONSE": json.dumps({"settled": bool(pay), "mock": True}),
            "X-Calibration-Note": reply.note,
            "X-Calibration-Profile": profile,
        })


def build_manifest() -> dict:
    """Ground truth for every (profile, resource): what the service does and what a
    correct evaluator should conclude. This is what the evaluator gets scored against."""
    expectations = {
        "honest": {"expected": "served", "deterministic": True,
                   "rationale": "correct and complete on every resource"},
        "flaky": {"expected": "mixed", "deterministic": False,
                  "rationale": f"correct ~{int(FLAKY_SUCCESS_RATE*100)}% of attempts, "
                               "errors otherwise, independent of phrasing; expect "
                               "no_response on failed rolls"},
        "brittle": {"expected": "phrasing-dependent", "deterministic": True,
                    "rationale": "served only when the query matches the expected pattern, "
                                 "not_served otherwise; always HTTP 200 so uptime "
                                 "monitoring cannot detect this"},
        "deadbeat": {"expected": "no_response", "deterministic": True,
                     "rationale": "HTTP 200 with an empty body after taking payment"},
        "truncator": {"expected": "partially_served or not_served", "deterministic": True,
                      "rationale": "well-formed but provenance stripped; should trip the "
                                   "disqualifiers about missing as-of markers and the "
                                   "requiredFields constraint"},
        "confabulator": {"expected": "mixed", "deterministic": False,
                         "rationale": "shape always correct, content fabricated ~50% of "
                                      "attempts; a judge grading form rather than content "
                                      "will score this too highly, which is the test"},
    }
    return {
        "generatedBy": "tools/calibration/services.py",
        "flakySuccessRate": FLAKY_SUCCESS_RATE,
        "resources": {r: {"price_usdc": PRICE_USDC[r], "truth": TRUTH[r]} for r in RESOURCES},
        "profiles": {
            p: {**expectations[p],
                "brittlePattern": BRITTLE_PATTERNS[RESOURCES[0]].pattern if p == "brittle" else None}
            for p in PROFILES
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="calibration services")
    ap.add_argument("--port", type=int, default=8402)
    ap.add_argument("--no-payment", action="store_true",
                    help="serve without requiring an X-PAYMENT header")
    ap.add_argument("--manifest", action="store_true", help="print the manifest and exit")
    args = ap.parse_args()

    if args.manifest:
        print(json.dumps(build_manifest(), indent=2))
        return

    Handler.require_payment = not args.no_payment
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"calibration services on http://127.0.0.1:{args.port}")
    print(f"  profiles:  {', '.join(PROFILES)}")
    print(f"  resources: {', '.join(RESOURCES)}")
    print(f"  example:   /honest/usdc-supply?q=total+USDC+supply+on+Arc&attemptId=a1")
    srv.serve_forever()


if __name__ == "__main__":
    main()
