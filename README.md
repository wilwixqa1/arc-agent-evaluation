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
  04-purpose-schema.md   design rationale for the purpose document

spec/
  purpose.schema.json    the purpose document schema (draft 2020-12)
  examples/              four sealed purposes, including a negative fixture

spec/
  rubric/v0.1.0.md       the judging protocol

tools/
  arc-census/            chain measurement tooling (no wallet required)
  purpose/               canonicalize, seal, validate and score purposes
  judge/                 rubric-driven evaluation, fixtures, Phase 0 harness
  calibration/           six x402 sellers with engineered quality profiles
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

## The purpose document

The core contribution. A structured statement of what a buying agent is trying to
achieve, sealed before the outcome is knowable, graded against afterward.

Two blocks. `constraints` is machine-checkable and no LLM touches it. `objective` is
LLM-graded and requires **disqualifiers**: specific ways the request could fail. That
field is the schema's main defence against self-serving purposes, because vacuous
disqualifiers are far harder to write than vacuous success criteria.

Specificity is scored from the document alone, before any response exists, so it can be
tracked over time as a drift metric. Real examples score 0.81 to 0.91; a deliberately
gamed fixture scores 0.14 while remaining schema-valid. The schema cannot stop
vagueness, so it measures it instead.

```bash
cd tools/purpose && pip install -r requirements.txt
python seal_examples.py
python tests/test_purpose.py
```

## The judge

The judge never gives an overall verdict. It answers one narrow yes-or-no question per
success criterion and per disqualifier, and the verdict is computed from those answers
by a deterministic rule. "Did the response state a block number above 59000000" is
answered the same way on repeated runs; "was this response good" is not.

Phase 0 tests that assumption before anything is built on it: 24 hand-labelled
fixtures, 3 repeats, no blockchain and no services involved. Bars are 90%
self-consistency and 80% agreement with the human label, on clear fixtures only.

```bash
cd tools/judge
python tests/test_judge.py        # 44 tests, no API key needed
python run_phase0.py --dry-run    # assemble all 24 prompts, call nothing
ANTHROPIC_API_KEY=... python run_phase0.py --repeats 3
```

## Calibration services

Six x402 sellers with known, deliberately engineered quality profiles, because a judge
can be perfectly self-consistent and consistently wrong. Grading responses whose
quality we already know is the only check on that.

108 attempts across 6 profiles, 6 phrasings and 3 repeats, using **only the
deterministic constraint checker with no judge involved**:

| profile | passes | constraint violated | no response |
|---|---|---|---|
| honest | 18 | 0 | 0 |
| flaky | 13 | 0 | 5 |
| brittle | 3 | 15 | 0 |
| deadbeat | 0 | 0 | 18 |
| truncator | 0 | 18 | 0 |
| confabulator | 18 | 0 | 0 |

An uptime monitor sees **103 of 108 attempts return HTTP 200**, so 95.4% uptime across
a population where one of six services is actually good. `deadbeat` takes payment,
returns nothing, and is 100% "up". `brittle` passes on its canonical phrasing and fails
on all five paraphrases while never erroring, which is invisible to liveness monitoring
by construction. `confabulator` passes every hard constraint with half its answers
fabricated, which is precisely the gap the judge exists to fill.

```bash
cd tools/calibration
python services.py --port 8402
python tests/test_calibration.py
```

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
