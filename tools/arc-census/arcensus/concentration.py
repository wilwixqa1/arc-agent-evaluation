"""Agent ownership concentration.

The direct analogue of the July 2026 ERC-8004 study's concentration analysis, which
reported Gini 0.733 on Ethereum, 0.708 on Base, and 0.134 on BSC, with the top 1% of
Ethereum wallets owning 58.5% of agents.

No event scanning required. The Blockscout holders endpoint returns the full ownership
distribution, sorted descending, through cursor pagination. Pagination is inherently
sequential, so the walk checkpoints to disk after every page and resumes from where it
stopped.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .explorer import Explorer


@dataclass
class Concentration:
    holders: int
    total_agents: int
    gini: float
    top1_pct_share: float
    top10_pct_share: float
    top_holder_share: float
    hhi: float
    mean_per_holder: float
    median_per_holder: float
    max_per_holder: int
    singletons: int
    singleton_share: float

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def gini(values: list[int]) -> float:
    """Gini coefficient of a distribution. 0 is perfect equality, 1 is one owner.

    Uses the sorted-rank formulation, which is exact rather than an approximation
    over binned data.
    """
    if not values:
        return 0.0
    xs = sorted(values)
    n = len(xs)
    total = sum(xs)
    if total == 0:
        return 0.0
    cumulative = sum((i + 1) * x for i, x in enumerate(xs))
    return (2.0 * cumulative) / (n * total) - (n + 1.0) / n


def hhi(values: list[int]) -> float:
    """Herfindahl-Hirschman index on ownership shares, 0..1."""
    total = sum(values)
    if total == 0:
        return 0.0
    return sum((v / total) ** 2 for v in values)


def walk_holders(
    address: str,
    checkpoint: Path,
    max_pages: int = 200,
    explorer: Explorer | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """Page through holders, appending to a checkpoint file. Resumable.

    Returns the checkpoint state. `done` is True once the endpoint stops handing back
    a cursor, which means the full distribution has been collected.
    """
    ex = explorer or Explorer()
    state: dict[str, Any] = (
        json.loads(checkpoint.read_text())
        if checkpoint.exists()
        else {"address": address, "cursor": None, "pages": 0, "holders": [], "done": False}
    )
    if state.get("done"):
        if verbose:
            print(f"  already complete: {len(state['holders'])} holders")
        return state

    t0 = time.time()
    for _ in range(max_pages):
        page = ex._get(f"/api/v2/tokens/{address}/holders", params=state["cursor"])
        if not page:
            break
        items = page.get("items", [])
        for it in items:
            state["holders"].append(
                [it["address"]["hash"].lower(), int(it["value"])]
            )
        state["pages"] += 1
        nxt = page.get("next_page_params")
        state["cursor"] = nxt
        if not nxt:
            state["done"] = True
            break

    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(json.dumps(state))
    if verbose:
        print(
            f"  pages={state['pages']} holders={len(state['holders'])} "
            f"done={state['done']} ({time.time()-t0:.0f}s this batch)"
        )
    return state


def analyze(holders: list[list]) -> Concentration:
    values = [int(v) for _, v in holders]
    values.sort(reverse=True)
    n = len(values)
    total = sum(values)

    def share(k: int) -> float:
        k = max(1, k)
        return round(100.0 * sum(values[:k]) / total, 2) if total else 0.0

    singles = sum(1 for v in values if v == 1)
    return Concentration(
        holders=n,
        total_agents=total,
        gini=round(gini(values), 4),
        top1_pct_share=share(int(n * 0.01)),
        top10_pct_share=share(int(n * 0.10)),
        top_holder_share=share(1),
        hhi=round(hhi(values), 6),
        mean_per_holder=round(total / n, 2) if n else 0.0,
        median_per_holder=values[n // 2] if n else 0,
        max_per_holder=values[0] if n else 0,
        singletons=singles,
        singleton_share=round(100.0 * singles / n, 2) if n else 0.0,
    )


BUCKETS = [(1, 1), (2, 4), (5, 9), (10, 49), (50, 99), (100, 499), (500, 10 ** 9)]


def bucket_report(holders: list[list]) -> list[dict]:
    """Holdings-size histogram. The shape matters more than the Gini: a high Gini
    driven by one whale and a high Gini driven by thousands of mid-size farming
    wallets are different phenomena with the same coefficient."""
    values = sorted((int(v) for _, v in holders), reverse=True)
    n, total = len(values), sum(values)
    out = []
    for lo, hi in BUCKETS:
        grp = [v for v in values if lo <= v <= hi]
        out.append({
            "range": f"{lo}" if lo == hi else (f"{lo}+" if hi > 10 ** 8 else f"{lo}-{hi}"),
            "holders": len(grp),
            "holders_pct": round(100.0 * len(grp) / n, 2) if n else 0.0,
            "agents": sum(grp),
            "agents_pct": round(100.0 * sum(grp) / total, 2) if total else 0.0,
        })
    return out
