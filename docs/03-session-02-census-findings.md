# Session 2 — Arc Testnet Census: Empirical Findings

**Date:** August 29, 2026
**Method:** direct JSON-RPC against `https://rpc.testnet.arc.io/` (chain ID 5042002)
plus the Arcscan Blockscout API. Everything below is measured, not sourced from
reporting. Reproducible scripts noted per section.

**Headline:** the supply risk was backwards. Arc testnet has far more registered
agents than Ethereum, BSC, and Base combined. Almost none of them are real. In a
random sample of 250 agents, **zero had a reachable service endpoint.**

---

## 1. Population

| Registry | Measure | Value |
|---|---|---|
| IdentityRegistry | Transfer events (mints + moves) | **887,911** |
| IdentityRegistry | Highest token ID observed | 887,839 |
| IdentityRegistry | Distinct holders | **47,215** |
| ReputationRegistry | Transactions | **18,948,867** |
| ValidationRegistry | Transactions | **110,198** |
| AgenticCommerce (8183) | Transactions | 599,248 |
| AgenticCommerce (8183) | `jobCounter()` | **182,367** |

For comparison, the July 2026 empirical study (§6.1 of the context file) counted
roughly 170,000 agents across Ethereum, BSC, and Base combined. **Arc testnet alone
has about five times that.**

All four contracts are ERC-1967 proxies. Implementations:

| Contract | Proxy | Implementation |
|---|---|---|
| IdentityRegistry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | `0x7274e874ca62410a93bd8bf61c69d8045e399c02` |
| ReputationRegistry | `0x8004B663056A597Dffe9eCcC1965A193B7388713` | `0x16e0fa7f7c56b9a767e34b192b51f921be31da34` |
| ValidationRegistry | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` | `0xdb31f5d9167f8ebc8b30fbbf814c4d297c2d7f99` |
| AgenticCommerce | `0x0747EEf0706327138c69792bF28Cd525089e4583` | `0xa316fd02827242d537f84730f8a37d0ba5fd351a` |

They are upgradeable. Any address you record in the context file should be treated as
the proxy, and the implementation re-resolved before you rely on an ABI.

Deployment blocks (binary search on `eth_getCode`): the three ERC-8004 registries at
blocks 29,241,340 to 29,241,349, roughly 156 days ago. AgenticCommerce at 33,908,011,
roughly 132 days ago.

---

## 2. The agents are not real

Random sample, seed 7, of 250 token IDs from 1 to 887,839. `tokenURI` read directly
from the contract.

| Result | Count | Share |
|---|---|---|
| No URI set | 1 | 0.4% |
| `data:application/json,` inline | 238 | 95.2% |
| `ipfs://` | 7 | 2.8% |
| `https://` | 4 | 1.6% |

> **Correction.** An earlier pass of this section reported 48 agents (19.2%) with no
> URI set. That was a measurement error, not a finding: the ad-hoc script used for the
> first run swallowed RPC rate-limit failures as empty results. Re-run through
> `arc-census`, which retries with backoff and distinguishes a revert from a transport
> failure, the real figure is 1 of 250. The reachability result is unchanged.

Of the 238 inline metadata documents, every one parsed cleanly, and:

| Signal | Count of 238 |
|---|---|
| Has a `services` array (ERC-8004 spec) | **0** |
| Has a `registrations` array (ERC-8004 spec) | **0** |
| Has a `type` field | 6 |
| Mentions x402 | **0** |
| Mentions MCP | **0** |
| Declares any http endpoint other than an image | **0** |

The only URL present in any of them is the Arcscan logo, used as the `image` field.

Name patterns after stripping the trailing hex suffix:

```
 109  Agent-XXXXXX
  56  Trader-XXXXXX
  50  Bridge-XXXXXX
   7  Agent-Mega-NNN
   5  hermes
   3  VAgent
```

Three templates account for 215 of 238, about 90%. This is scripted registration, not
developers registering services.

### The ten non-inline URIs, individually checked

Only **4 of 250** declare anything resembling a service endpoint, and all four fail.

- **3** point at Circle's quickstart IPFS CID
  `bafkreibdi6623n3xpf7ymk62ckb4bo75o3qemwkpfvp5i25j66itxvsoei`. Exactly the
  copy-paste behavior predicted in §5 point 2. All three timed out on the gateway.
- **4** point at **fabricated CIDs** such as
  `ipfs://bafkreigf22dd3fc341a724715108d76367496e0`. These are not valid CIDv1 strings,
  they are hex padded to look like one. All returned HTTP 500.
- **3** point at `https://arc-agent.example.com/...`, the RFC 2606 reserved example
  domain. Connection refused.
- **1** points at a catbox.moe upload. HTTP 502.

**Zero of 250 sampled agents have a reachable service endpoint.** Not a low
percentage. Zero.

### What that bounds

With 0 successes in 250 trials, the rule of three puts the 95% upper bound on the true
rate at about 1.2%. Chain-wide that is an upper bound of roughly 10,600 reachable
agents, and the realistic figure is far lower given the sample was uniformly random
and the failure mode was categorical rather than marginal.

The July 2026 paper found 3% on Ethereum, 4% on BSC, and 15% on Base. **Arc is
materially worse than all three.**

---

## 2b. Ownership concentration: a different shape from Ethereum

Full holder distribution, not a sample. All 47,444 holders walked via the Blockscout
holders endpoint, which returns ownership sorted descending through cursor pagination
and needs no event scanning.

| Measure | Arc testnet | Ethereum | Base | BSC |
|---|---|---|---|---|
| **Gini** | **0.8879** | 0.733 | 0.708 | 0.134 |
| Top 1% share | 25.5% | 58.5% | — | — |
| Top 10% share | **92.0%** | — | — | — |
| Largest single holder | 904 agents (0.1%) | — | — | — |
| Median holding | **1** | — | — | — |

Arc is the most unequal chain measured. But the Gini alone is misleading, because a
high coefficient driven by one whale and a high coefficient driven by thousands of
mid-size wallets are different phenomena with the same number. Arc is the second kind.

Holdings histogram (47,444 holders, 888,277 agents):

| Holdings | Holders | Share of holders | Agents | Share of agents |
|---|---|---|---|---|
| 1 | 31,367 | 66.11% | 31,367 | 3.53% |
| 2-4 | 9,572 | 20.18% | 25,097 | 2.83% |
| 5-9 | 1,163 | 2.45% | 6,621 | 0.75% |
| 10-49 | 2,013 | 4.24% | 37,080 | 4.17% |
| 50-99 | 213 | 0.45% | 18,452 | 2.08% |
| **100-499** | **2,998** | **6.32%** | **705,203** | **79.39%** |
| 500+ | 118 | 0.25% | 64,457 | 7.26% |

**Roughly 3,000 wallets each holding between 100 and 499 agents account for 79% of the
entire population.** The largest holder has 904, so there is no dominant entity: the
top 100 holders combined hold only 6.2%.

That is not the Ethereum pattern, where 2.6% of registration transactions produced
48.3% of agents through batching. It is a flat farm: thousands of wallets each running
what looks like the same script to a similar depth. Whether that is one operator with
3,000 wallets or many operators converging on the same behaviour is not separable from
ownership data alone; it would need funding-graph analysis, which is future work.

Two supporting observations:

- The modal holding is 1 (31,367 wallets), and the next two modes are **2** (6,272
  wallets) and **4** (2,653). Circle's quickstart creates exactly two wallets. That is
  suggestive rather than conclusive, but it is the tutorial's fingerprint.
- Summing holder balances gives **888,277 agents**, which cross-checks against the
  887,911 Transfer events and the highest observed token ID of 888,262.

Reproduce with `python census.py concentration`. The walk is resumable; re-run until
`done` is true.

---

## 3. ERC-8183: three open questions closed

Sample of 120 jobs drawn uniformly from 182,367, seed 3.

| Status | Count |
|---|---|
| Completed | 60 |
| Open | 54 |
| Funded | 3 |
| Rejected | 2 |
| Submitted | 1 |

### O7 is resolved: `commitmentRef` does not exist

The deployed implementation is verified on Arcscan. Its source contains **zero**
occurrences of `commitmentRef` and zero of `intent`. The job struct is:

```
jobs(uint256) -> (uint256 id, address client, address provider, address evaluator,
                  string description, uint256 budget, uint256 expiredAt,
                  uint8 status, address hook)
```

No commitment field. The context file's §4.3 point 3 should be marked resolved and
negative.

**Workable substitute using only what exists.** The lifecycle already gives you three
write slots at exactly the right moments:

| Slot | Type | Written by | When | Use for |
|---|---|---|---|---|
| `description` | string | client | `createJob`, before anything happens | **purpose hash** |
| `deliverable` | bytes32 | provider | `submit` | response hash |
| `reason` | bytes32 | evaluator | `complete` / `reject` | verdict hash |

`description` is set at creation and never mutated. That is a genuine pre-commitment
slot. You do not need `commitmentRef` and you do not need a new contract.

### Hooks are permissioned, and unused

The implementation exposes `setHookWhitelist(address, bool)` and
`whitelistedHooks(address)`. A hook must be whitelisted by an `ADMIN_ROLE` holder
before it can be attached to a job.

**This kills §11 item 7 as a solo project.** You cannot deploy an IACPHook that
enforces evaluator independence and evidence-backed feedback, because you cannot
whitelist it. That becomes a proposal to Circle, not a build.

Measured usage: **hook == `address(0)` in 120 of 120 jobs. 100%.** Nobody uses the
extension point, which is unsurprising given nobody can.

### Evaluator independence is mostly absent, and fees are switched off

**`evaluator == client` in 81 of 120 jobs, 67.5%.** Circle's tutorial pattern
("the client also acts as the evaluator") reproduced at scale, now with a number
attached. §5 point 5 confirmed empirically.

The remaining 32.5% use a distinct evaluator address, but a distinct address is not a
distinct party. Section 5 point 3 of the context file describes the exact two-wallet
pattern the quickstart teaches. Treat 67.5% as a floor on collapsed evaluation, not an
estimate.

Fee parameters exist but are zeroed:

```
evaluatorFeeBP()  = 0
platformFeeBP()   = 0
platformTreasury  = 0xcbe5b97a069be3e4b5398663790731fb76ab620d
paymentToken      = 0x3600000000000000000000000000000000000000  (USDC)
```

Only `setEvaluatorFee` under `ADMIN_ROLE` can change this. **Funding evaluation out of
escrow is not currently available to you.** The context file §4.3 point 2 said the
economics were "already a parameter, not something we would have to invent." True, but
the parameter is set to zero and you cannot set it. Update that note.

Job descriptions are mostly tutorial boilerplate: "Arc automation job" (19),
"ERC-8183 job" (13), "ERC-8183 demo job on Arc Testnet" (6). A handful are real-looking
tasks such as competitor DEX analysis and cross-chain arbitrage scans.

---

## 4. Corrections to the context file

| Section | Current | Corrected |
|---|---|---|
| §3.1 block time | "~2s (UNVERIFIED, conflicts with sub-second)" | **530ms average**, per Arcscan stats. Resolved, no conflict. |
| §3.1 gas token | "USDC (not a volatile native token)" | Still true, but ARC now exists as a separate governance asset. Say so explicitly. |
| §3.1 testnet volume | "150M+ tx in first 90 days" | 244.1M as of May 5, 2026 per the ARC whitepaper; total blocks now 59.4M |
| §3.4 addresses | listed as contracts | All four are **ERC-1967 proxies**. Record implementations separately. |
| §4.3 pt 2 evaluator fees | "already a parameter" | Parameter exists, **set to 0**, admin-only. Not available to you. |
| §4.3 pt 3 `commitmentRef` | UNVERIFIED | **Resolved: does not exist** in the deployed implementation |
| §4.3 pt 1 `hook` | "the designed extension point" | **Whitelist-gated.** Permissionless hook deployment is not possible. |
| §7.4 | "Arc has none of them" | Correct, and now explained: there is nothing on Arc worth monitoring |
| §10 risks | no supply risk listed | Add it, then mark it resolved in the opposite direction |
| Chain IDs | absent | testnet 5042002, mainnet 5042 |

---

## 5. What this does to the project

The mystery shopper as originally scoped **cannot run on Arc testnet today.** There
are no live paid services to shop. That is not a setback, it is the finding.

Three consequences, in order of importance.

### 5.1 The census is a publishable result on its own

Nobody has measured Arc. The paper covered Ethereum, BSC, and Base through May 2026
and explicitly excluded the ValidationRegistry for lack of a mainnet deployment. Arc
has 110,198 ValidationRegistry transactions. That dataset does not exist anywhere in
the literature.

You can write "The State of ERC-8004 on Arc" this week, with:
- 887,911 agents, 47,215 holders, and a 0-of-250 endpoint reachability result
- 67.5% evaluator collapse in 8183, and 100% hook non-adoption
- a metadata compliance failure rate of 100% against the ERC-8004 spec fields
- direct attribution of the failure modes to specific lines in Circle's own tutorials

That publishes before mainnet, needs no new infrastructure, and lands exactly on
Circle's stated H2 priority. It is also the strongest possible argument that outcome
measurement is needed, which is the setup for the shopper.

### 5.2 Calibration services move from "recommended" to "required"

Phase 1 option B in the build plan is now the only option for Arc. If you want to
demonstrate the shopper on Arc, you have to deploy the sellers yourself. The upside
stands: engineered quality profiles give you ground truth, which is the only way to
show measurement integrity.

### 5.3 The Base pivot is now the main path for real-service data

Option A from the build plan is no longer a fallback, it is the plan. Shop the large
Base x402 population, publish verdicts, and use Arc as the record and comparison
layer. The cross-chain comparison you had as §11 item 11 becomes the v1 spine:
**an ecosystem with services but no outcome measurement, next to an ecosystem with
neither.**

---

## 6. Revised next actions

- [ ] Decide: census paper first, or shopper first. The census is faster, publishable,
      and unblocked. Recommend census first.
- [ ] Scale the sample from 250 to ~3,000 agents for publication-grade confidence
      intervals. The tooling exists, it is a rate-limit problem, so get a QuickNode or
      Chainstack key.
- [ ] Sample the ReputationRegistry (18.9M transactions) for the self-dealing rate.
      This is the direct Arc analogue of the paper's Sybil analysis and is the single
      biggest remaining unknown.
- [ ] Check whether the 47,215 holders concentrate the way the paper found (Gini 0.73
      on Ethereum). Batch-registration detection: how many agents came from how many
      transactions.
- [ ] Enumerate the Base x402 service population properly before committing to 5.3.
- [ ] Still open and unaffected: O1 purpose schema, O8 evaluator model and rubric.

---

## 7. Reproduction

Scripts in the working directory: `rpc.py` (contract probes), `deploy.py` (deployment
block binary search), `sample.py` (tokenURI sampling), `analyze.py` (metadata
analysis), `outliers.py` (non-inline URI fetching), `impl.py` (proxy resolution),
`jobs2.py` (8183 job sampling).

Note on method: the public RPC rate-limits `eth_getLogs` to 10,000-block ranges and
throttles hard above about 8 concurrent requests via Cloudflare. Full event scans need
a keyed provider. The Blockscout API at `testnet.arcscan.app/api/v2/` has no such limit
and is the better source for aggregate counts.
