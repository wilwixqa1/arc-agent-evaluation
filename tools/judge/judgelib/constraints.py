"""Deterministic constraint checking.

The hard half of a purpose document. Every check here is arithmetic or string
comparison. No model is involved, so a violation is a fact rather than an opinion and
is not contestable.

This runs BEFORE the judge and its output feeds rule 2 of the verdict derivation
(spec/rubric/v0.1.0.md §2). A response that violated a stated constraint did not serve
the stated purpose, however good its prose.

Design notes:

- Every check returns `not_applicable` when the purpose did not set that constraint.
  Silence is distinguished from a pass, so a purpose with no constraints cannot be
  mistaken for one that passed everything.
- Path lookup accepts dotted paths and JSON pointers, and walks lists by index. Real
  responses nest.
- Numeric extraction tolerates strings, because services return "48221930114" as often
  as they return the integer.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from typing import Any

Status = str  # "pass" | "fail" | "not_applicable" | "indeterminate"


@dataclass
class Check:
    constraint: str
    status: Status
    detail: str
    expected: Any = None
    actual: Any = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConstraintResult:
    checks: list[Check] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    indeterminate: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "violations": self.violations,
            "indeterminate": self.indeterminate,
            "checks": [c.as_dict() for c in self.checks],
        }


# --------------------------------------------------------------------------
# path lookup
# --------------------------------------------------------------------------

_MISSING = object()


def lookup(obj: Any, path: str) -> Any:
    """Resolve a dotted path or JSON pointer. Returns _MISSING if absent."""
    if path.startswith("/"):
        parts = [p.replace("~1", "/").replace("~0", "~") for p in path.strip("/").split("/")]
    else:
        parts = [p for p in re.split(r"[.\[\]]", path) if p]
    cur = obj
    for p in parts:
        if isinstance(cur, dict):
            if p not in cur:
                return _MISSING
            cur = cur[p]
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return _MISSING
        else:
            return _MISSING
    return cur


def as_number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def as_text(body: Any) -> str:
    return body if isinstance(body, str) else json.dumps(body)


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------

def check(purpose: dict, attempt: dict) -> ConstraintResult:
    """Evaluate every hard constraint in `purpose` against `attempt`.

    `attempt` carries the response body plus observed metadata:
        {"body": ..., "latencyMs": int, "pricePaidUsdc": float,
         "contentType": str, "error": str|None}
    """
    con = purpose.get("constraints") or {}
    body = attempt.get("body")
    res = ConstraintResult()

    def add(name: str, status: Status, detail: str, expected=None, actual=None):
        res.checks.append(Check(name, status, detail, expected, actual))
        if status == "fail":
            res.violations.append(name)
        elif status == "indeterminate":
            res.indeterminate.append(name)

    # -- price ----------------------------------------------------------
    cap = con.get("maxPriceUsdc")
    if cap is None:
        add("maxPriceUsdc", "not_applicable", "no price ceiling set")
    else:
        paid = as_number(attempt.get("pricePaidUsdc"))
        if paid is None:
            add("maxPriceUsdc", "indeterminate", "price paid not recorded", cap, None)
        elif paid > cap:
            add("maxPriceUsdc", "fail", f"paid {paid} over ceiling {cap}", cap, paid)
        else:
            add("maxPriceUsdc", "pass", f"paid {paid} within {cap}", cap, paid)

    # -- latency --------------------------------------------------------
    lat_cap = con.get("maxLatencyMs")
    if lat_cap is None:
        add("maxLatencyMs", "not_applicable", "no latency ceiling set")
    else:
        lat = as_number(attempt.get("latencyMs"))
        if lat is None:
            add("maxLatencyMs", "indeterminate", "latency not recorded", lat_cap, None)
        elif lat > lat_cap:
            add("maxLatencyMs", "fail", f"{int(lat)}ms over ceiling {lat_cap}ms", lat_cap, lat)
        else:
            add("maxLatencyMs", "pass", f"{int(lat)}ms within {lat_cap}ms", lat_cap, lat)

    # -- format ---------------------------------------------------------
    fmt = con.get("responseFormat")
    if not fmt:
        add("responseFormat", "not_applicable", "no format required")
    else:
        actual = "json" if isinstance(body, (dict, list)) else "text"
        if fmt == "json":
            ok = isinstance(body, (dict, list))
            if not ok and isinstance(body, str):
                try:
                    json.loads(body)
                    ok, actual = True, "json (as string)"
                except (json.JSONDecodeError, TypeError):
                    ok = False
            add("responseFormat", "pass" if ok else "fail",
                f"expected json, got {actual}", fmt, actual)
        elif fmt in ("text", "markdown"):
            ok = isinstance(body, str)
            add("responseFormat", "pass" if ok else "fail",
                f"expected {fmt}, got {actual}", fmt, actual)
        else:
            add("responseFormat", "indeterminate", f"no checker for format {fmt!r}", fmt, actual)

    # -- required fields ------------------------------------------------
    req = con.get("requiredFields") or []
    if not req:
        add("requiredFields", "not_applicable", "none required")
    else:
        missing = []
        for p in req:
            v = lookup(body, p)
            # Present but null or empty string counts as missing: the field exists to
            # carry a value, and an empty one carries none.
            if v is _MISSING or v is None or v == "":
                missing.append(p)
        add("requiredFields", "fail" if missing else "pass",
            f"missing {missing}" if missing else f"all {len(req)} present", req, missing)

    # -- substrings -----------------------------------------------------
    text = as_text(body).lower()
    need = con.get("requiredSubstrings") or []
    if not need:
        add("requiredSubstrings", "not_applicable", "none required")
    else:
        absent = [s for s in need if s.lower() not in text]
        add("requiredSubstrings", "fail" if absent else "pass",
            f"absent {absent}" if absent else f"all {len(need)} present", need, absent)

    forbid = con.get("forbiddenSubstrings") or []
    if not forbid:
        add("forbiddenSubstrings", "not_applicable", "none forbidden")
    else:
        found = [s for s in forbid if s.lower() in text]
        add("forbiddenSubstrings", "fail" if found else "pass",
            f"found {found}" if found else "none present", forbid, found)

    # -- numeric bounds -------------------------------------------------
    bounds = con.get("numericBounds") or []
    if not bounds:
        add("numericBounds", "not_applicable", "none set")
    else:
        for b in bounds:
            name = f"numericBounds[{b['path']}]"
            raw = lookup(body, b["path"])
            if raw is _MISSING:
                add(name, "fail", f"path {b['path']} absent from response", b, None)
                continue
            val = as_number(raw)
            if val is None:
                add(name, "fail", f"value at {b['path']} is not numeric: {raw!r}", b, raw)
                continue
            lo, hi = b.get("min"), b.get("max")
            if lo is not None and val < lo:
                add(name, "fail", f"{val} below min {lo}", b, val)
            elif hi is not None and val > hi:
                add(name, "fail", f"{val} above max {hi}", b, val)
            else:
                add(name, "pass", f"{val} within bounds", b, val)

    # -- schema ---------------------------------------------------------
    ref = con.get("responseSchemaRef")
    if not ref:
        add("responseSchemaRef", "not_applicable", "no schema required")
    else:
        schema = _resolve_schema(ref, purpose)
        if schema is None:
            add("responseSchemaRef", "indeterminate", f"could not resolve {ref}", ref, None)
        else:
            try:
                from jsonschema import Draft202012Validator
                errs = [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}"
                        for e in Draft202012Validator(schema).iter_errors(body)]
                add("responseSchemaRef", "fail" if errs else "pass",
                    "; ".join(errs[:3]) if errs else "validates", ref, errs[:3] or None)
            except ImportError:
                add("responseSchemaRef", "indeterminate", "jsonschema not installed", ref, None)

    # -- freshness ------------------------------------------------------
    fresh = con.get("freshness")
    if not fresh:
        add("freshness", "not_applicable", "no freshness requirement")
    else:
        fld = fresh.get("asOfField")
        max_age = fresh.get("maxAgeSeconds")
        if not fld:
            add("freshness", "indeterminate", "no asOfField named", fresh, None)
        else:
            raw = lookup(body, fld)
            if raw is _MISSING:
                add("freshness", "fail", f"as-of field {fld} absent", fresh, None)
            else:
                # An as-of marker that is present but uninterpretable is indeterminate,
                # not a violation: the purpose asked for provenance and got some.
                observed = attempt.get("asOfObserved")
                age = as_number(attempt.get("asOfAgeSeconds"))
                if age is None and observed is None:
                    add("freshness", "indeterminate",
                        f"{fld} present ({raw!r}) but age not computable without a reference",
                        fresh, raw)
                elif age is not None and age > max_age:
                    add("freshness", "fail", f"age {age}s exceeds {max_age}s", fresh, age)
                else:
                    add("freshness", "pass", f"age {age}s within {max_age}s", fresh, age)

    return res


def _resolve_schema(ref: str, purpose: dict) -> dict | None:
    if ref.startswith("#"):
        return lookup(purpose, ref[1:]) or None
    from pathlib import Path
    p = Path(ref)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return None
    return None
