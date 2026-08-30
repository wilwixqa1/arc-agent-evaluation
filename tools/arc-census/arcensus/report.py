"""Render collected census data into a markdown report."""
from __future__ import annotations
from datetime import datetime, timezone


def _pct(k, n):
    return f"{100.0*k/n:.1f}%" if n else "n/a"


def render(totals, agents, reputation, jobs) -> str:
    L = []
    A = L.append
    A("# Arc ERC-8004 / ERC-8183 Census\n")
    A(f"Generated {datetime.now(timezone.utc).isoformat()}\n")

    if totals:
        A("## Chain\n")
        A(f"- RPC: `{totals.get('rpc')}`  chain id `{totals.get('chain_id')}`")
        A(f"- Block height: {int(totals.get('block_number', 0)):,}")
        if totals.get("avg_block_time_ms"):
            A(f"- Average block time: {totals['avg_block_time_ms']} ms")
        A("\n### Contracts\n")
        A("| Contract | Proxy | Implementation | Transactions |")
        A("|---|---|---|---|")
        for name, e in (totals.get("contracts") or {}).items():
            tx = (e.get("counters") or {}).get("transactions_count", "-")
            A(f"| {name} | `{e['proxy']}` | `{e.get('implementation') or 'not a proxy'}` | {tx} |")
        tok = totals.get("identity_token") or {}
        if tok:
            A(f"\n- AgentIdentity holders: **{tok.get('token_holders_count')}**")
            A(f"- AgentIdentity transfers: **{tok.get('transfers_count')}**")
        p = totals.get("agentic_commerce_params") or {}
        if p:
            A(f"\n- ERC-8183 jobs: **{p.get('job_counter')}**")
            A(f"- evaluatorFeeBP: **{p.get('evaluator_fee_bp')}**, "
              f"platformFeeBP: **{p.get('platform_fee_bp')}**")

    if agents:
        n = agents["sampled"]
        A("\n## Agent identity and reachability\n")
        A(f"Random sample of **{n}** agents from **{agents.get('max_agent_id', 0):,}** "
          f"registered (seed {agents.get('seed')}).\n")
        A("| Metric | Count | Share |")
        A("|---|---|---|")
        for label, key in [
            ("No tokenURI set", "no_uri"),
            ("Declares a service endpoint", "declares_service_endpoint"),
            ("**Reachable endpoint**", "reachable"),
            ("Uses Circle quickstart CID", "quickstart_cid"),
            ("Malformed IPFS CID", "malformed_cid"),
            ("Placeholder host (example.com)", "placeholder_host"),
            ("Has ERC-8004 `services` array", "spec_has_services"),
            ("Has ERC-8004 `registrations` array", "spec_has_registrations"),
            ("Has `type` field", "spec_has_type"),
            ("Mentions x402", "mentions_x402"),
            ("Mentions MCP", "mentions_mcp"),
        ]:
            v = agents.get(key, 0)
            A(f"| {label} | {v} | {_pct(v, n)} |")
        A(f"\nURI schemes: `{agents.get('schemes')}`")
        if agents.get("reachable") == 0:
            ub = agents.get("reachable_upper_bound_95_pct")
            A(f"\n**Zero reachable endpoints in {n} samples.** Rule of three puts the "
              f"95% upper bound on the true rate at {ub}%.")
        if agents.get("name_patterns"):
            A("\nName patterns (trailing hash stripped):\n")
            A("```")
            for k, v in agents["name_patterns"].items():
                A(f"{v:5d}  {k or '(blank)'}")
            A("```")

    if jobs:
        n = jobs["sampled"]
        A("\n## ERC-8183 jobs\n")
        A(f"Random sample of **{n}** of **{jobs.get('job_counter', 0):,}** jobs.\n")
        A(f"- Status: `{jobs.get('status')}`")
        A(f"- **evaluator == client: {jobs['evaluator_is_client']} "
          f"({jobs['evaluator_is_client_pct']}%)**")
        A(f"- evaluator == provider: {jobs.get('evaluator_is_provider')}")
        A(f"- **hook set (not address(0)): {jobs['hook_set']} ({jobs['hook_set_pct']}%)**")
        A(f"- Zero budget: {jobs.get('zero_budget')}")
        A("\nTop descriptions:\n")
        A("```")
        for d, c in (jobs.get("top_descriptions") or [])[:10]:
            A(f"{c:5d}  {d!r}")
        A("```")

    if reputation:
        A("\n## Reputation\n")
        n = reputation.get("agents_with_feedback", 0)
        A(f"- Agents sampled: {reputation.get('sampled_agents')}")
        A(f"- With any feedback: **{n}** ({reputation.get('agents_with_feedback_pct')}%)")
        A(f"- **Owner rated own agent: {reputation.get('owner_rated_own_agent')} "
          f"({reputation.get('owner_rated_own_agent_pct')}% of rated)**")
        A(f"- Single-client agents: {reputation.get('single_client_agents')} "
          f"({reputation.get('single_client_pct')}%)")
        A(f"- Distinct reviewers: {reputation.get('distinct_reviewers')}, "
          f"top reviewer share {reputation.get('top_reviewer_share_pct')}%")
        A(f"- Value range: {reputation.get('value_min')} to {reputation.get('value_max')}, "
          f"above 100: {reputation.get('values_above_100')}, "
          f"below zero: {reputation.get('values_below_zero')}")
        A(f"- valueDecimals distribution: `{reputation.get('value_decimals_distribution')}`")
        A(f"- Distinct tags: {reputation.get('distinct_tags')}")

    A("\n---\n")
    A("Reproduce: `python census.py all`. Set `ARC_RPC_URL` to a keyed provider "
      "and raise `ARC_RPC_CONCURRENCY` to scale the sample size.")
    return "\n".join(L) + "\n"
