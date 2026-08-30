"""ReputationRegistry analysis.

The registry's only integrity rule is that an agent's owner cannot rate its own
agent. Circle's quickstart defeats it by creating a second wallet. This module
measures how widespread that is, without event scanning: getClients() and
readAllFeedback() expose everything through plain eth_call.

Deployed ABI (differs from several published descriptions):
  giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
               string tag1, string tag2, string endpoint,
               string feedbackURI, bytes32 feedbackHash)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field

from .chain import ArcClient, CONTRACTS

# Verified against the deployed implementation ABI, in declaration order.
FEEDBACK_TUPLE = (
    "address[]",    # clients
    "uint64[]",     # feedbackIndexes
    "int128[]",     # values
    "uint8[]",      # valueDecimals
    "string[]",     # tag1s
    "string[]",     # tag2s
    "bool[]",       # revokedStatuses
)


@dataclass
class AgentReputation:
    agent_id: int
    owner: str | None
    clients: list[str] = field(default_factory=list)
    values: list[int] = field(default_factory=list)
    value_decimals: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    feedback_clients: list[str] = field(default_factory=list)
    revoked: int = 0
    error: str | None = None

    @property
    def owner_rated_self(self) -> bool:
        if not self.owner:
            return False
        return self.owner.lower() in {c.lower() for c in self.clients}

    @property
    def single_client(self) -> bool:
        return len(self.clients) == 1

    def as_dict(self) -> dict:
        d = asdict(self)
        d["owner_rated_self"] = self.owner_rated_self
        d["single_client"] = self.single_client
        d["feedback_count"] = len(self.values)
        return d


def owner_of(client: ArcClient, agent_id: int) -> str | None:
    try:
        (owner,) = client.call(
            CONTRACTS["identity"], "ownerOf(uint256)", ["uint256"], [agent_id], ["address"]
        )
        return owner
    except Exception:
        return None


def get_clients(client: ArcClient, agent_id: int) -> list[str]:
    try:
        (clients,) = client.call(
            CONTRACTS["reputation"], "getClients(uint256)", ["uint256"], [agent_id], ["address[]"]
        )
        return list(clients)
    except Exception:
        return []


def read_all_feedback(client: ArcClient, agent_id: int, clients: list[str]) -> tuple | None:
    """readAllFeedback(uint256,address[],string,string,bool)"""
    try:
        return client.call(
            CONTRACTS["reputation"],
            "readAllFeedback(uint256,address[],string,string,bool)",
            ["uint256", "address[]", "string", "string", "bool"],
            [agent_id, clients, "", "", False],
            FEEDBACK_TUPLE,
        )
    except Exception:
        return None


def profile_agent(client: ArcClient, agent_id: int) -> AgentReputation:
    rec = AgentReputation(agent_id=agent_id, owner=owner_of(client, agent_id))
    rec.clients = get_clients(client, agent_id)
    if not rec.clients:
        return rec
    data = read_all_feedback(client, agent_id, rec.clients)
    if data is None:
        rec.error = "readAllFeedback reverted"
        return rec
    clients, indexes, values, decimals, tag1s, tag2s, revoked = data
    keep = [i for i, rv in enumerate(revoked) if not rv]
    rec.feedback_clients = [clients[i] for i in keep]
    rec.values = [int(values[i]) for i in keep]
    rec.value_decimals = [int(decimals[i]) for i in keep]
    rec.tags = [t for i in keep for t in (tag1s[i], tag2s[i]) if t]
    rec.revoked = len(revoked) - len(keep)
    return rec


def sample_reputation(client: ArcClient, agent_ids: list[int]) -> list[AgentReputation]:
    out: list[AgentReputation] = []
    for rec in client.map(lambda i: profile_agent(client, i), agent_ids):
        if rec is not None:
            out.append(rec)
    return out


def summarize(records: list[AgentReputation]) -> dict:
    rated = [r for r in records if r.clients]
    n_rated = len(rated)

    def pct(k: int, d: int) -> float:
        return round(100.0 * k / d, 2) if d else 0.0

    self_rated = [r for r in rated if r.owner_rated_self]
    all_values = [v for r in rated for v in r.values]
    # A raw value is uninterpretable without its valueDecimals. Mixed scales in one
    # registry is the commensurability failure (C1) the ERC-8004 literature warns of.
    normalized = [
        v / (10 ** d)
        for r in rated
        for v, d in zip(r.values, r.value_decimals)
    ]
    scales = Counter()
    for r in rated:
        for d in r.value_decimals:
            scales[d] += 1

    # Reviewer concentration: how many distinct clients account for the feedback
    reviewer_counts: dict[str, int] = defaultdict(int)
    for r in rated:
        for c in r.clients:
            reviewer_counts[c.lower()] += 1
    top = Counter(reviewer_counts).most_common(10)
    total_edges = sum(reviewer_counts.values())

    return {
        "sampled_agents": len(records),
        "agents_with_feedback": n_rated,
        "agents_with_feedback_pct": pct(n_rated, len(records)),
        "owner_rated_own_agent": len(self_rated),
        "owner_rated_own_agent_pct": pct(len(self_rated), n_rated),
        "single_client_agents": sum(1 for r in rated if r.single_client),
        "single_client_pct": pct(sum(1 for r in rated if r.single_client), n_rated),
        "distinct_reviewers": len(reviewer_counts),
        "total_reviewer_edges": total_edges,
        "top_reviewer_share_pct": pct(top[0][1], total_edges) if top else 0.0,
        "top_reviewers": top,
        "value_decimals_distribution": dict(scales),
        "raw_value_min": min(all_values) if all_values else None,
        "raw_value_max": max(all_values) if all_values else None,
        "normalized_min": round(min(normalized), 3) if normalized else None,
        "normalized_max": round(max(normalized), 3) if normalized else None,
        "normalized_above_100": sum(1 for v in normalized if v > 100),
        "normalized_below_zero": sum(1 for v in normalized if v < 0),
        "distinct_scales_in_use": len(scales),
        "scale_conflict": len(scales) > 1,
        "feedback_records": len(all_values),
        "distinct_tags": len({t for r in rated for t in r.tags}),
    }
