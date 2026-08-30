"""ERC-8183 AgenticCommerce job analysis.

Deployed struct (implementation behind the proxy, verified on Arcscan):
  jobs(uint256) -> (id, client, provider, evaluator, description,
                    budget, expiredAt, status, hook)

Note there is no commitmentRef and no intent field. The three usable
pre/post commitment slots are:
  description  string   client   set at createJob, never mutated
  deliverable  bytes32  provider set at submit
  reason       bytes32  evaluator set at complete/reject
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, asdict

from .chain import ArcClient, CONTRACTS

STATUS = ["Open", "Funded", "Submitted", "Completed", "Rejected", "Expired"]

JOB_OUT = (
    "uint256", "address", "address", "address", "string",
    "uint256", "uint256", "uint8", "address",
)

ZERO = "0x0000000000000000000000000000000000000000"


@dataclass
class Job:
    job_id: int
    client: str
    provider: str
    evaluator: str
    description: str
    budget: int
    expired_at: int
    status: str
    hook: str

    @property
    def evaluator_is_client(self) -> bool:
        return self.evaluator.lower() == self.client.lower()

    @property
    def evaluator_is_provider(self) -> bool:
        return self.evaluator.lower() == self.provider.lower()

    @property
    def has_hook(self) -> bool:
        return self.hook.lower() != ZERO

    def as_dict(self) -> dict:
        d = asdict(self)
        d["evaluator_is_client"] = self.evaluator_is_client
        d["evaluator_is_provider"] = self.evaluator_is_provider
        d["has_hook"] = self.has_hook
        return d


def job_counter(client: ArcClient) -> int:
    (n,) = client.call(CONTRACTS["agentic_commerce"], "jobCounter()", [], [], ["uint256"])
    return int(n)


def contract_params(client: ArcClient) -> dict:
    def one(sig, typ):
        try:
            return client.call(CONTRACTS["agentic_commerce"], sig, [], [], [typ])[0]
        except Exception:
            return None

    return {
        "job_counter": one("jobCounter()", "uint256"),
        "evaluator_fee_bp": one("evaluatorFeeBP()", "uint256"),
        "platform_fee_bp": one("platformFeeBP()", "uint256"),
        "platform_treasury": one("platformTreasury()", "address"),
        "payment_token": one("paymentToken()", "address"),
    }


def get_job(client: ArcClient, job_id: int) -> Job | None:
    try:
        row = client.call(
            CONTRACTS["agentic_commerce"], "jobs(uint256)", ["uint256"], [job_id], JOB_OUT
        )
    except Exception:
        return None
    jid, cl, pr, ev, desc, budget, exp, status, hook = row
    return Job(
        job_id=int(jid),
        client=cl,
        provider=pr,
        evaluator=ev,
        description=desc,
        budget=int(budget),
        expired_at=int(exp),
        status=STATUS[int(status)] if int(status) < len(STATUS) else str(status),
        hook=hook,
    )


def sample_jobs(client: ArcClient, n: int, total: int, seed: int = 3) -> list[Job]:
    rng = random.Random(seed)
    ids = rng.sample(range(1, total + 1), min(n, total))
    return [j for j in client.map(lambda i: get_job(client, i), ids) if j is not None]


def summarize(jobs: list[Job]) -> dict:
    n = len(jobs)

    def pct(k: int) -> float:
        return round(100.0 * k / n, 2) if n else 0.0

    ev_is_client = sum(1 for j in jobs if j.evaluator_is_client)
    hooked = sum(1 for j in jobs if j.has_hook)
    return {
        "sampled": n,
        "status": dict(Counter(j.status for j in jobs)),
        "evaluator_is_client": ev_is_client,
        "evaluator_is_client_pct": pct(ev_is_client),
        "evaluator_is_provider": sum(1 for j in jobs if j.evaluator_is_provider),
        "hook_set": hooked,
        "hook_set_pct": pct(hooked),
        "zero_budget": sum(1 for j in jobs if j.budget == 0),
        "distinct_clients": len({j.client.lower() for j in jobs}),
        "distinct_providers": len({j.provider.lower() for j in jobs}),
        "distinct_evaluators": len({j.evaluator.lower() for j in jobs}),
        "top_descriptions": Counter(j.description[:70] for j in jobs).most_common(10),
    }
