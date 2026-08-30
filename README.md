# Arc Agent Evaluation

Measuring whether agentic services on Arc actually work, rather than whether they
are online.

Every existing quality tool in the x402 ecosystem measures uptime, latency, envelope
compliance, and price stability. None measures whether the response was correct,
complete, or useful. This repository holds the research, the measurement tooling, and
eventually the evaluation system that closes that gap.

---

## Current status

**Pre-build.** Research and landscape work is complete. The first measurement tool is
built and running against Arc testnet. The evaluation system itself is designed but
not started, for a reason documented below.

### Headline finding

Arc testnet has **887,911 agent registrations**, roughly five times the combined total
across Ethereum, BSC, and Base reported in the July 2026 ERC-8004 empirical study.

In a uniform random sample of 250 of them, **zero had a reachable service endpoint.**

| | |
|---|---|
| Inline `data:` template metadata | 95.2% |
| Declares anything resembling a service endpoint | 4 of 250 |
| Declares an ERC-8004 `services` array | **0** |
| Mentions x402 | **0** |
| Mentions MCP | **0** |
| **Reachable service endpoint** | **0 of 250** |

Three name templates (`Agent-`, `Trader-`, `Bridge-`) account for 90% of sampled
metadata. The handful of agents pointing at external URIs use Circle's quickstart
IPFS CID, fabricated CIDs that are hex padded to look valid, or the RFC 2606 reserved
domain `example.com`.

Alongside that, from live contract reads:

- **ERC-8183: `evaluator == client` in 67.5%** of sampled jobs. The standard's entire
  purpose is an independent third party attesting completion before escrow releases.
- **ERC-8183: `hook` is `address(0)` in 100%** of sampled jobs. The extension point is
  whitelist-gated by an admin role, so permissionless use is not possible.
- **ERC-8183: `evaluatorFeeBP` and `platformFeeBP` are both 0**, and only an admin can
  change them. Funding evaluation out of escrow is not currently available to builders.
- **Reputation: `valueDecimals` is used inconsistently within the same registry.**
  Of 2,295 decoded feedback records, 1,742 use 2 decimals, 549 use 0, and 4 use 1. A
  raw value of `85` means 0.85 to one writer and 85 to another. Scores are not
  comparable, which is the commensurability failure the literature predicted, now
  measured.
- **Reputation: 959 distinct reviewer addresses produced 1,008 reviews**, top reviewer
  at 0.5%. Almost every reviewer rates once and disappears.

### What this means for the project

The mystery shopper as originally scoped cannot run on Arc testnet, because there is
nothing to shop. That reframes the work rather than blocking it: the census is a
publishable result on its own, and it is the argument for why outcome measurement is
needed.

See [`docs/03-session-02-census-findings.md`](docs/03-session-02-census-findings.md)
for the full analysis and the revised plan.

---

## Repository layout

```
docs/
  01-context.md          project source of truth: research, standards, decisions
  02-build-plan.md       architecture, phases, session roadmap, UI direction
  03-session-02-...md    empirical census findings and corrections to 01

tools/
  arc-census/            measurement tooling (Python, no wallet required)
    census.py            CLI
    arcensus/            chain client, explorer client, analysis modules
    data/                collected samples and summaries
```

## Quick start

```bash
cd tools/arc-census
pip install -r requirements.txt
python census.py totals
python census.py agents --n 250 --probe
python census.py jobs --n 120
python census.py reputation --n 140
python census.py report
```

Nothing here needs a wallet, a private key, or testnet funds. It is all read-only.

To scale past the public RPC throttle, set `ARC_RPC_URL` to a keyed provider and raise
`ARC_RPC_CONCURRENCY`. See [`tools/arc-census/README.md`](tools/arc-census/README.md).

## Reference

Arc testnet, chain ID `5042002`. All four registries are ERC-1967 proxies; the
implementation addresses are resolved at runtime by `census.py totals`.

| Contract | Proxy |
|---|---|
| ERC-8004 IdentityRegistry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| ERC-8004 ReputationRegistry | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |
| ERC-8004 ValidationRegistry | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` |
| ERC-8183 AgenticCommerce | `0x0747EEf0706327138c69792bF28Cd525089e4583` |
| USDC (gas token) | `0x3600000000000000000000000000000000000000` |

## License

MIT. This is intended as common-good research tooling.
