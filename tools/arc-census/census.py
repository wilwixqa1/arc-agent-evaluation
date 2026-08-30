#!/usr/bin/env python3
"""Arc ERC-8004 / ERC-8183 census.

Usage:
    python census.py totals
    python census.py agents --n 250 --seed 7 --probe
    python census.py reputation --n 150 --seed 7
    python census.py jobs --n 120 --seed 3
    python census.py all --agents 250 --jobs 120 --reputation 150
    python census.py report

Set ARC_RPC_URL to a keyed provider and raise ARC_RPC_CONCURRENCY to scale past
the public endpoint's throttle.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from arcensus import identity, jobs as jobs_mod, reputation as rep_mod  # noqa: E402
from arcensus import concentration as conc_mod  # noqa: E402
from arcensus.chain import ArcClient, CONTRACTS  # noqa: E402
from arcensus.explorer import Explorer  # noqa: E402

OUT = Path(os.environ.get("ARC_CENSUS_OUT", "data"))


def _write(name: str, obj) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if name.endswith(".jsonl"):
        with path.open("w") as fh:
            for row in obj:
                fh.write(json.dumps(row, default=str) + "\n")
    else:
        path.write_text(json.dumps(obj, indent=2, default=str))
    print(f"  wrote {path}")
    return path


def _load(name: str):
    path = OUT / name
    if not path.exists():
        return None
    if name.endswith(".jsonl"):
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return json.loads(path.read_text())


def cmd_totals(args) -> dict:
    client, ex = ArcClient(), Explorer()
    print("Reading chain and explorer totals...")
    out = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "rpc": client.url,
        "chain_id": client.chain_id(),
        "block_number": client.block_number(),
        "contracts": {},
    }
    try:
        stats = ex.stats()
        out["avg_block_time_ms"] = stats.get("average_block_time")
        out["total_blocks"] = stats.get("total_blocks")
        out["total_addresses"] = stats.get("total_addresses")
    except Exception as exc:
        out["explorer_error"] = str(exc)

    for name, addr in CONTRACTS.items():
        if name == "usdc":
            continue
        entry = {"proxy": addr}
        try:
            entry["implementation"] = client.implementation_of(addr)
        except Exception:
            entry["implementation"] = None
        try:
            entry["counters"] = ex.address_counters(addr)
        except Exception:
            pass
        out["contracts"][name] = entry

    try:
        out["identity_token"] = ex.token_counters(CONTRACTS["identity"])
    except Exception:
        pass
    out["agentic_commerce_params"] = jobs_mod.contract_params(client)
    _write("totals.json", out)
    print(json.dumps(out, indent=2, default=str)[:1600])
    return out


def cmd_agents(args) -> dict:
    client, ex = ArcClient(), Explorer()
    max_id = args.max_id or identity.max_agent_id(client, ex)
    print(f"Sampling {args.n} of {max_id:,} agents (seed {args.seed})...")
    t0 = time.time()
    records = identity.sample_agents(client, args.n, max_id, seed=args.seed)
    print(f"  fetched {len(records)} tokenURIs in {time.time()-t0:.0f}s")
    if args.probe:
        print("  probing declared endpoints...")
        identity.probe_reachability(records)
    summary = identity.summarize(records)
    summary["max_agent_id"] = max_id
    summary["seed"] = args.seed
    _write("agents.jsonl", [r.as_dict() for r in records])
    _write("agents_summary.json", summary)
    print(json.dumps(summary, indent=2)[:2000])
    return summary


def cmd_reputation(args) -> dict:
    client, ex = ArcClient(), Explorer()
    max_id = args.max_id or identity.max_agent_id(client, ex)
    import random

    ids = random.Random(args.seed).sample(range(1, max_id + 1), min(args.n, max_id))
    print(f"Profiling reputation for {len(ids)} agents...")
    t0 = time.time()
    records = rep_mod.sample_reputation(client, ids)
    print(f"  done in {time.time()-t0:.0f}s")
    summary = rep_mod.summarize(records)
    _write("reputation.jsonl", [r.as_dict() for r in records])
    _write("reputation_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str)[:2000])
    return summary


def cmd_jobs(args) -> dict:
    client = ArcClient()
    total = jobs_mod.job_counter(client)
    print(f"Sampling {args.n} of {total:,} ERC-8183 jobs (seed {args.seed})...")
    js = jobs_mod.sample_jobs(client, args.n, total, seed=args.seed)
    summary = jobs_mod.summarize(js)
    summary["job_counter"] = total
    summary["contract_params"] = jobs_mod.contract_params(client)
    _write("jobs.jsonl", [j.as_dict() for j in js])
    _write("jobs_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str)[:2000])
    return summary


def cmd_concentration(args) -> dict:
    """Walk the full holder distribution and compute concentration statistics.

    Resumable: pagination is sequential, so state is checkpointed after every batch.
    Re-run until `done` is True.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    cp = OUT / "holders_checkpoint.json"
    print(f"Walking holders for {CONTRACTS['identity']} (checkpoint {cp})...")
    st = conc_mod.walk_holders(CONTRACTS["identity"], cp, max_pages=args.max_pages)
    if not st["done"]:
        print("  incomplete, re-run this command to continue")
        return {}
    c = conc_mod.analyze(st["holders"])
    summary = c.as_dict()
    summary["buckets"] = conc_mod.bucket_report(st["holders"])
    _write("concentration_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def cmd_report(args) -> None:
    from arcensus.report import render

    text = render(
        _load("totals.json"),
        _load("agents_summary.json"),
        _load("reputation_summary.json"),
        _load("jobs_summary.json"),
    )
    path = OUT / "REPORT.md"
    path.write_text(text)
    print(f"  wrote {path}\n")
    print(text)


def cmd_all(args) -> None:
    cmd_totals(args)
    cmd_agents(argparse.Namespace(n=args.agents, seed=args.seed, probe=True, max_id=None))
    cmd_jobs(argparse.Namespace(n=args.jobs, seed=args.seed_jobs, max_id=None))
    cmd_reputation(argparse.Namespace(n=args.reputation, seed=args.seed, max_id=None))
    cmd_concentration(argparse.Namespace(max_pages=1200))
    cmd_report(args)


def main() -> None:
    p = argparse.ArgumentParser(description="Arc ERC-8004 / ERC-8183 census")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("totals").set_defaults(fn=cmd_totals)

    a = sub.add_parser("agents")
    a.add_argument("--n", type=int, default=250)
    a.add_argument("--seed", type=int, default=7)
    a.add_argument("--max-id", type=int, default=None, dest="max_id")
    a.add_argument("--probe", action="store_true")
    a.set_defaults(fn=cmd_agents)

    r = sub.add_parser("reputation")
    r.add_argument("--n", type=int, default=150)
    r.add_argument("--seed", type=int, default=7)
    r.add_argument("--max-id", type=int, default=None, dest="max_id")
    r.set_defaults(fn=cmd_reputation)

    j = sub.add_parser("jobs")
    j.add_argument("--n", type=int, default=120)
    j.add_argument("--seed", type=int, default=3)
    j.add_argument("--max-id", type=int, default=None, dest="max_id")
    j.set_defaults(fn=cmd_jobs)

    al = sub.add_parser("all")
    al.add_argument("--agents", type=int, default=250)
    al.add_argument("--jobs", type=int, default=120)
    al.add_argument("--reputation", type=int, default=150)
    al.add_argument("--seed", type=int, default=7)
    al.add_argument("--seed-jobs", type=int, default=3, dest="seed_jobs")
    al.set_defaults(fn=cmd_all)

    c = sub.add_parser("concentration")
    c.add_argument("--max-pages", type=int, default=400, dest="max_pages")
    c.set_defaults(fn=cmd_concentration)

    sub.add_parser("report").set_defaults(fn=cmd_report)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
