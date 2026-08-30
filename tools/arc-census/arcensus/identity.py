"""Agent sampling and ERC-8004 metadata compliance scoring.

The question this module answers: of the agents registered on this chain, how many
are actually reachable services rather than registry entries?
"""
from __future__ import annotations

import json
import random
import re
import urllib.parse
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Iterable

import requests

from .chain import ArcClient, CONTRACTS

# Metadata URI published by Circle's "register your first AI agent" quickstart.
# Every developer who follows the happy path points at this.
QUICKSTART_CID = "bafkreibdi6623n3xpf7ymk62ckb4bo75o3qemwkpfvp5i25j66itxvsoei"

# Domains reserved by RFC 2606 or otherwise definitionally non-functional.
PLACEHOLDER_HOSTS = ("example.com", "example.org", "example.net", "localhost", "127.0.0.1")

# Hosts that only ever appear as an image field, not a service endpoint.
NON_SERVICE_HOSTS = ("arcscan.app", "ipfs.io", "gateway.pinata.cloud", "w3s.link")

CIDV1_RE = re.compile(r"^ba[a-z2-7]{57,}$")


@dataclass
class AgentRecord:
    agent_id: int
    uri: str | None
    uri_scheme: str
    metadata: dict | None
    parse_error: str | None
    # compliance
    has_services: bool
    has_registrations: bool
    has_type: bool
    mentions_x402: bool
    mentions_mcp: bool
    # reachability
    declared_endpoints: list[str]
    is_quickstart_cid: bool
    is_malformed_cid: bool
    is_placeholder_host: bool
    reachable: bool | None = None
    reach_detail: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def classify_scheme(uri: str | None) -> str:
    if not uri:
        return "none"
    if uri.startswith("data:"):
        return "data"
    if uri.startswith("ipfs://"):
        return "ipfs"
    if uri.startswith("http://") or uri.startswith("https://"):
        return "http"
    return "other"


def parse_metadata(uri: str) -> tuple[dict | None, str | None]:
    """Return (metadata, error). Only inline data URIs are parsed here."""
    if not uri.startswith("data:"):
        return None, None
    _, _, body = uri.partition(",")
    try:
        return json.loads(urllib.parse.unquote(body)), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def service_endpoints(meta: dict | None, uri: str) -> list[str]:
    """URLs that could plausibly be a service endpoint.

    Excludes image hosts and explorer assets, which is what almost every farmed
    registration puts in its `image` field and which would otherwise inflate the
    reachability number to nearly 100%.
    """
    found: list[str] = []
    if isinstance(meta, dict):
        for svc in meta.get("services") or []:
            if isinstance(svc, dict):
                for key in ("endpoint", "url", "uri", "serviceEndpoint"):
                    if isinstance(svc.get(key), str):
                        found.append(svc[key])
            elif isinstance(svc, str):
                found.append(svc)
        for key in ("endpoint", "url", "serviceEndpoint", "api", "a2a", "mcp"):
            val = meta.get(key)
            if isinstance(val, str) and val.startswith("http"):
                found.append(val)
        blob = json.dumps(meta)
        image = meta.get("image") if isinstance(meta.get("image"), str) else ""
        for url in re.findall(r'https?://[^\s"\\\']+', blob):
            if url == image:
                continue
            if any(h in url for h in NON_SERVICE_HOSTS):
                continue
            found.append(url)
    elif uri.startswith("http"):
        found.append(uri)
    # dedupe, preserve order
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def build_record(agent_id: int, uri: str | None) -> AgentRecord:
    scheme = classify_scheme(uri)
    meta, err = (None, None) if not uri else parse_metadata(uri)
    blob = json.dumps(meta) if isinstance(meta, dict) else (uri or "")
    endpoints = service_endpoints(meta, uri or "")

    is_quickstart = bool(uri and QUICKSTART_CID in uri)
    malformed_cid = False
    if uri and uri.startswith("ipfs://"):
        cid = uri[len("ipfs://"):].split("/")[0]
        malformed_cid = not bool(CIDV1_RE.match(cid))
    placeholder = any(h in (uri or "") for h in PLACEHOLDER_HOSTS) or any(
        h in e for e in endpoints for h in PLACEHOLDER_HOSTS
    )

    return AgentRecord(
        agent_id=agent_id,
        uri=uri,
        uri_scheme=scheme,
        metadata=meta,
        parse_error=err,
        has_services=isinstance(meta, dict) and isinstance(meta.get("services"), list),
        has_registrations=isinstance(meta, dict) and isinstance(meta.get("registrations"), list),
        has_type=isinstance(meta, dict) and "type" in meta,
        mentions_x402="402" in blob,
        mentions_mcp=bool(re.search(r"\bmcp\b", blob, re.I)),
        declared_endpoints=endpoints,
        is_quickstart_cid=is_quickstart,
        is_malformed_cid=malformed_cid,
        is_placeholder_host=placeholder,
    )


def fetch_token_uri(client: ArcClient, agent_id: int) -> str | None:
    try:
        (uri,) = client.call(
            CONTRACTS["identity"], "tokenURI(uint256)", ["uint256"], [agent_id], ["string"]
        )
        return uri or None
    except Exception:
        return None


def max_agent_id(client: ArcClient, explorer=None) -> int:
    """Highest minted agent id. totalSupply is not implemented, so read the
    newest instance from the explorer and fall back to a probe."""
    if explorer is not None:
        try:
            items = explorer.token_instances(CONTRACTS["identity"], pages=1)
            if items:
                return max(int(i["id"]) for i in items)
        except Exception:
            pass
    lo, hi = 1, 1
    while fetch_token_uri(client, hi) is not None or _exists(client, hi):
        lo, hi = hi, hi * 2
        if hi > 2 ** 32:
            break
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _exists(client, mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def _exists(client: ArcClient, agent_id: int) -> bool:
    try:
        client.call(
            CONTRACTS["identity"], "ownerOf(uint256)", ["uint256"], [agent_id], ["address"]
        )
        return True
    except Exception:
        return False


def sample_agents(
    client: ArcClient, n: int, max_id: int, seed: int = 7, ids: Iterable[int] | None = None
) -> list[AgentRecord]:
    if ids is None:
        rng = random.Random(seed)
        ids = rng.sample(range(1, max_id + 1), min(n, max_id))
    ids = list(ids)
    records: list[AgentRecord] = []
    for agent_id, uri in zip(ids, client.map(lambda i: fetch_token_uri(client, i), ids)):
        records.append(build_record(agent_id, uri))
    return records


def probe_reachability(records: list[AgentRecord], timeout: int = 12, workers: int = 6) -> None:
    """Attempt to reach each declared endpoint. Mutates records in place."""
    from concurrent.futures import ThreadPoolExecutor

    targets = [r for r in records if r.declared_endpoints or r.uri_scheme in ("http", "ipfs")]

    def probe(rec: AgentRecord):
        urls = list(rec.declared_endpoints)
        if not urls and rec.uri:
            if rec.uri.startswith("ipfs://"):
                urls = ["https://ipfs.io/ipfs/" + rec.uri[7:]]
            elif rec.uri.startswith("http"):
                urls = [rec.uri]
        for url in urls[:3]:
            try:
                r = requests.get(url, timeout=timeout)
                if r.status_code < 400:
                    rec.reachable = True
                    rec.reach_detail = f"HTTP {r.status_code} {url}"
                    return
                rec.reach_detail = f"HTTP {r.status_code} {url}"
            except Exception as exc:
                rec.reach_detail = f"{type(exc).__name__} {url}"
        rec.reachable = False

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(probe, targets))
    for rec in records:
        if rec.reachable is None:
            rec.reachable = False
            rec.reach_detail = rec.reach_detail or "no endpoint declared"


def summarize(records: list[AgentRecord]) -> dict:
    n = len(records)
    schemes = Counter(r.uri_scheme for r in records)
    with_uri = [r for r in records if r.uri]
    parsed = [r for r in records if isinstance(r.metadata, dict)]
    reachable = [r for r in records if r.reachable]
    uri_counts = Counter(r.uri for r in with_uri)

    def pct(k: int) -> float:
        return round(100.0 * k / n, 2) if n else 0.0

    return {
        "sampled": n,
        "schemes": dict(schemes),
        "no_uri": schemes.get("none", 0),
        "no_uri_pct": pct(schemes.get("none", 0)),
        "distinct_uris": len(uri_counts),
        "quickstart_cid": sum(1 for r in records if r.is_quickstart_cid),
        "malformed_cid": sum(1 for r in records if r.is_malformed_cid),
        "placeholder_host": sum(1 for r in records if r.is_placeholder_host),
        "parsed_inline_json": len(parsed),
        "spec_has_services": sum(1 for r in records if r.has_services),
        "spec_has_registrations": sum(1 for r in records if r.has_registrations),
        "spec_has_type": sum(1 for r in records if r.has_type),
        "mentions_x402": sum(1 for r in records if r.mentions_x402),
        "mentions_mcp": sum(1 for r in records if r.mentions_mcp),
        "declares_service_endpoint": sum(1 for r in records if r.declared_endpoints),
        "reachable": len(reachable),
        "reachable_pct": pct(len(reachable)),
        "reachable_upper_bound_95_pct": round(100.0 * 3.0 / n, 3) if reachable == [] and n else None,
        "name_patterns": dict(
            Counter(
                re.sub(r"[-_][0-9A-Za-z]{4,}$", "", str((r.metadata or {}).get("name", "")))
                for r in parsed
            ).most_common(10)
        ),
    }
