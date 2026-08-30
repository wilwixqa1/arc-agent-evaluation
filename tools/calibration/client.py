#!/usr/bin/env python3
"""x402 shopper client.

Walks the real x402 flow against the calibration services: request, receive 402 with
payment requirements, present a payment header, receive the resource. Settlement is
mocked locally; the envelope and the retry are real, so the same client works against
a live service without change.

Produces attempt records in the shape `judgelib.build_record` expects, including the
observed latency and price the deterministic constraint checker needs.

Calibration notes travel in headers, never in the body, and are stripped into
`groundTruth` before the attempt is handed on. The judge must never see them.
"""
from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict, field


@dataclass
class Attempt:
    attemptId: str
    profile: str
    resource: str
    phrasingId: str | None
    query: str
    body: object = None
    status: int | None = None
    latencyMs: int | None = None
    pricePaidUsdc: float | None = None
    error: str | None = None
    paymentRequired: dict | None = None
    groundTruth: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)

    def for_judge(self) -> dict:
        """The judge sees no ground truth and no profile identity."""
        d = self.as_dict()
        d.pop("groundTruth", None)
        d.pop("profile", None)
        return d


def _mock_payment_header(req: dict) -> str:
    """A structurally valid X-PAYMENT header for the `exact` scheme.

    Base64 of a payload with the fields a facilitator would need. Signature is a
    placeholder because nothing settles locally; on a real run this is where the
    EIP-3009 authorization signed by the buyer wallet goes.
    """
    accept = req["accepts"][0]
    payload = {
        "x402Version": 1,
        "scheme": accept["scheme"],
        "network": accept["network"],
        "payload": {
            "authorization": {
                "from": "0x0000000000000000000000000000000000000001",
                "to": accept["payTo"],
                "value": accept["maxAmountRequired"],
                "validAfter": "0",
                "validBefore": str(int(time.time()) + accept.get("maxTimeoutSeconds", 60)),
                "nonce": "0x" + "00" * 32,
            },
            "signature": "0x" + "00" * 65,
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def fetch(base: str, profile: str, resource: str, query: str, attempt_id: str,
          phrasing_id: str | None = None, timeout: int = 20) -> Attempt:
    qs = urllib.parse.urlencode({"q": query, "attemptId": attempt_id})
    url = f"{base.rstrip('/')}/{profile}/{resource}?{qs}"
    att = Attempt(attemptId=attempt_id, profile=profile, resource=resource,
                  phrasingId=phrasing_id, query=query)
    t0 = time.time()

    def call(headers: dict):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    status, headers, raw = call({})
    if status == 402:
        try:
            att.paymentRequired = json.loads(raw)
        except json.JSONDecodeError:
            att.error = "malformed 402 envelope"
            att.latencyMs = int((time.time() - t0) * 1000)
            return att
        accept = att.paymentRequired["accepts"][0]
        att.pricePaidUsdc = int(accept["maxAmountRequired"]) / 10 ** accept["extra"]["decimals"]
        status, headers, raw = call({"X-PAYMENT": _mock_payment_header(att.paymentRequired)})

    att.latencyMs = int((time.time() - t0) * 1000)
    att.status = status
    try:
        att.body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        att.body = raw.decode(errors="replace")
    if status >= 400:
        att.error = f"HTTP {status}"
        att.body = None
    # Strip calibration metadata out of the attempt and into ground truth.
    note = headers.get("X-Calibration-Note")
    if note:
        att.groundTruth = {"note": note, "profile": headers.get("X-Calibration-Profile")}
    return att


def sweep(base: str, profiles: list[str], resource: str, phrasings: list[tuple[str, str]],
          repeats: int) -> list[Attempt]:
    out = []
    for p in profiles:
        for pid, text in phrasings:
            for r in range(repeats):
                out.append(fetch(base, p, resource, text, f"{p}:{resource}:{pid}:r{r}", pid))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8402")
    ap.add_argument("--resource", default="usdc-supply")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--out", default="attempts.json")
    args = ap.parse_args()

    from phrasings import PHRASINGS
    from services import PROFILES

    phr = [(p["phrasingId"], p["text"]) for p in PHRASINGS[args.resource]]
    atts = sweep(args.base, list(PROFILES), args.resource, phr, args.repeats)
    json.dump([a.as_dict() for a in atts], open(args.out, "w"), indent=2)
    print(f"{len(atts)} attempts -> {args.out}")


if __name__ == "__main__":
    main()
