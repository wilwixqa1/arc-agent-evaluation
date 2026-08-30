# Arc Agent Evaluation — Context and Research

**Status:** Research complete. Measurement tooling built and run. Evaluation system designed, not started.
**Last updated:** August 30, 2026 (session 2)
**Owner:** Will Wendt

## How to use this file

This is the source of truth for the project. It carries everything a future session
(human or model) needs to pick up without re-doing research.

Claims are marked one of three ways:

- **MEASURED** — verified directly against chain state or a primary contract read in
  session 2. Reproducible with `tools/arc-census`.
- **UNVERIFIED** — sourced from secondary reporting, not confirmed against primary docs
  or on-chain data. Verify before relying on it.
- Unmarked claims come from primary documentation or first-party sources.

Companion documents:
- `docs/02-build-plan.md` — architecture, phases, session roadmap, UI direction
- `docs/03-session-02-census-findings.md` — full empirical results and method notes

---

# 1. What we are building

## 1.1 One-line pitch

Everyone measures whether agentic services are *up*. Nobody measures whether they
are *right*. And Arc has neither.

## 1.2 The project

A **mystery shopper for agentic services**. A swarm of synthetic buyer agents that:

1. Declare a structured **purpose** before spending (what they are trying to achieve,
   what would count as success, constraints, budget)
2. Bind that purpose cryptographically to the transaction
3. Send the same purpose to a service **several different ways** (phrasing variations)
4. Collect the results
5. Have an evaluator grade, in words, whether the stated purpose was actually served
6. Publish everything: purposes, phrasings, raw results, verdicts, rubrics

## 1.3 What makes it different

**Outcome, not liveness.** Every existing x402 quality tool measures uptime, latency,
402-envelope compliance, price stability, settlement volume, and SSL/header hygiene.
None measure whether the response was correct, complete, or useful. This is the
difference between "is the restaurant open" and "is the food good."

**Variance under paraphrase.** Every existing scorer treats a service as a single point
estimate. The swarm produces a distribution. "Works 90% of the time regardless of
phrasing" and "works 90% if phrased right, 20% otherwise" produce identical uptime
scores and are completely different products. Nobody in this ecosystem measures this.

## 1.4 Why this is honest work and not free lunch

Uptime probing scales to 25,000 endpoints because it is one HTTP call and a status
code. Semantic evaluation does not scale that way. It needs a declared purpose, a real
request, an LLM judge, and ideally several of each.

Realistic shape: **20 services evaluated deeply, not 25,000 shallowly.** Depth is
defensible precisely because breadth is already taken.

## 1.5 Framing

Originally treated as a hackathon-scale project for Arc. Session 2 established there is
no hackathon scheduled around mainnet launch (§2.5), so the framing is now a
publication timed to the launch window, with the census as the first output.

---

# 2. Strategic context

## 2.1 The timing fact, revised

**Arc public mainnet launches September 16, 2026.** Testnet is live now.

Session 1 recorded "the testnet window closes September 16." **That was wrong.**
Testnets are not retired at mainnet launch, and Arc is still investing in this one: a
v0.8.0 "Zero8" hardfork lands on testnet September 3, 2026 at 3:00pm UTC, changing gas
accounting and state-clearing semantics at the execution layer with no new
developer-facing APIs.

What closes on September 16 is the **attention window**, not the environment. Testnet
remains the only place you can spawn synthetic buyers, spend freely, send deliberately
malformed requests, and run adversarial agents without anyone getting hurt. That
property is permanent.

## 2.2 Circle's stated priority

From the Q2 2026 earnings release (August 5, 2026):

> After shipping payment infrastructure for agents in H1, Circle launched Agent Stack
> in May 2026 — currently home to 900+ paid services — with 99.3% of x402 agent-payment
> volume settling in USDC. Circle will turn to a more fulsome agentic product roadmap
> in H2 that includes **enabling agents to earn**.

H1 was agents paying. H2 is agents earning. Anything built should sit on the earning
side. There is no standalone "H2 Arc roadmap" document. The two relevant sources are
the January 29, 2026 product vision blog post and this earnings line.

## 2.3 Circle Q2 2026 numbers (context, not load-bearing)

| Metric | Value | Change |
|---|---|---|
| USDC in circulation | $73.3B | +19% YoY |
| USDC onchain volume (Q2) | $14.8T | +151% YoY |
| Total revenue + reserve income | $701M | +7% YoY |
| Adjusted EBITDA | $143M | +8% YoY |
| Net income (continuing ops) | $48M | +$530M YoY |
| Circle Payments Network | $14.7B annualized | +76% QoQ |
| CPN financial institutions | 175 | +29% QoQ |
| Arc ecosystem/institutional builders | 100+ | — |

Circle holds a federal trust bank charter (OCC), plus NYDFS-approved Circle New York
Trust.

## 2.4 Arc validator cohort

Founding third-party validators: BlackRock, DTCC, Galaxy, Global Payments, ICE,
Mastercard, MoneyGram, SBI Group, Standard Chartered, Sumitomo Corporation, Visa.
Circle is also a validator.

- BlackRock expected to deploy BUIDL on Arc
- DTCC to enable tokenization of DTC-custodied assets on Arc
- BNY added USDC mint/redeem in its Digital Asset Custody platform
- Mastercard and Visa also participate in the x402 Foundation

The September 16 mainnet launch will unveil privacy capabilities, an agent stack for
programmable finance, tokenized RWA support, a composable app framework for onchain
workflows, and AI-powered tools for building applications and smart contracts. That
last item is worth watching as a competitive risk (§10).

## 2.5 Hackathons and events

**No hackathon is scheduled around the September 16 launch.** Checked session 2.

Cadence has been roughly quarterly across three organizers:

| Event | Dates | Organizer |
|---|---|---|
| Agentic Commerce on Arc | Jan 9 to 24, 2026 | lablab.ai |
| Encode x Arc Enterprise & DeFi | Feb 27 to Mar 1, 2026 | Encode Club, London |
| Agentic Economy on Arc (Nanopayments) | Apr 20 to 26, 2026 | lablab.ai |
| Stablecoins Commerce Stack Challenge | Apr 14 to Aug 9, 2026 | — |
| Programmable Money | Jul 13 to Aug 22, 2026 | Arc House + Encode Club |

Both of the last two closed in August. A Q4 event timed to mainnet is likely but not
announced. Watch the Arc House events page, Encode Club programmes, lablab.ai, and the
Arc Discord.

Recurring and open to anyone: **Technical Office Hours**, free webinar roughly every
two weeks, 12:00pm GMT (September 3) and 3:00pm GMT (September 17). Replays posted.
The September 17 session is the first technical Q&A after mainnet and is the best
low-cost visibility opportunity.

**Mainnet launch livestream:** September 16, 6:00 to 7:30pm GMT.

Circle DevRel names attached to the hackathons: Corey Cooper, Jenna Teeman, Anthony
Kelani, Blessing Adesiji, Sam Sealey.

### What past hackathon projects tell us

Winners were developer tooling with an obvious path to production, not novel research.
First place in January went to **OmniAgentPay** (a Python SDK wrapping Circle
Developer-Controlled Wallets with atomic spending guards plus a universal `pay()` that
routes to direct USDC transfer, x402, or CCTP). Second was **Arc Merchant**
(autonomous x402 micropayments).

Two submissions sit near our territory:

- **RSoft Agentic Bank** — KYA (Know Your Agent), AP2 for authorized spending,
  LangGraph multi-agent risk scoring. Uses AP2 the way we plan to, then scores risk
  rather than outcome.
- An **API Wallet agent** — pay-per-request API/data/compute over x402 with Gemini
  routing to select providers and enforce budgets. Provider selection with no outcome
  data, which is exactly the hole D9 identifies in routing.

None grade whether a service delivered. §7's conclusion holds against this evidence.

**Useful design transfer:** OmniAgentPay's spending guards are constraints declared
before spending and enforced mechanically. That is the machine-checkable subset of our
purpose document. It supports the hard/soft split in O1.

---

# 3. Arc technical reference

## 3.1 Chain properties

| Property | Value |
|---|---|
| Type | Open Layer 1, EVM compatible |
| Gas token | **USDC** |
| Gas cost | ~0.006 USDC per transaction |
| Consensus | Malachite (BFT, Tendermint lineage) |
| Finality | Deterministic, sub-second |
| **Average block time** | **530 ms** (MEASURED, Arcscan stats) |
| Testnet chain ID | **5042002** (`0x4cef52`) (MEASURED) |
| Mainnet chain ID | **5042** |
| Testnet launch | October 28, 2025 |
| Mainnet launch | September 16, 2026 |
| Account abstraction | ERC-4337 and EIP-7702 native |
| Privacy | Opt-in, configurable, with selective disclosure |
| Post-quantum | Signature support planned at mainnet |

**Block time resolved.** Session 1 recorded "~2s (UNVERIFIED, conflicts with sub-second
claims)." Measured average is 530 ms. There is no conflict.

**ARC token.** Circle published the ARC whitepaper in May 2026 and closed a $222M
presale at a $3B fully diluted valuation, 10 billion initial supply, for governance,
security, and the future proof-of-stake network. **USDC remains the gas token.** The
session 1 phrasing "not a volatile native token" now reads as wrong and should be
stated as: gas is USDC; ARC is a separate governance and coordination asset.

**Testnet volume.** 244.1M transactions as of May 5, 2026 per the ARC whitepaper.
Block height passed 59.4M in August 2026. The session 1 figure of "150M+ in first 90
days" is stale but not contradicted.

## 3.2 Endpoints and tools

| Resource | URL |
|---|---|
| Docs | https://docs.arc.io (also resolves at docs.arc.network) |
| Docs index for LLMs | https://docs.arc.io/llms.txt |
| Testnet RPC | https://rpc.testnet.arc.io/ (MEASURED, live) |
| Testnet explorer | https://testnet.arcscan.app (Blockscout) |
| Explorer API | https://testnet.arcscan.app/api/v2/ |
| Faucet | https://faucet.circle.com |
| Console faucet | https://console.circle.com/faucet |
| Developer console | https://console.circle.com |
| Community / events | https://community.arc.io |
| Arc MCP server | See https://docs.arc.io/ai/mcp.md |

`viem` ships an `arcTestnet` chain export. Standard tooling works: Foundry, Hardhat,
ethers, wagmi, web3.py.

**Rate limits (MEASURED).** The public RPC caps `eth_getLogs` at a 10,000-block range
and throttles hard above roughly 8 concurrent requests via Cloudflare. Full event scans
need a keyed provider (QuickNode, Chainstack, GetBlock). The Blockscout API has no such
limits and is the better source for aggregate counts.

## 3.3 Circle Skills (relevant to Claude Code workflow)

```
/plugin marketplace add circlefin/skills
/plugin install circle-skills@circle
```

Or: `npx skills add circlefin/skills`

Available skills: `use-arc`, `use-usdc`, `use-circle-wallets`,
`use-developer-controlled-wallets`, `use-user-controlled-wallets`,
`use-modular-wallets`, `use-gateway`, `use-smart-contract-platform`.

## 3.4 Contract addresses (Arc Testnet)

**All four registries are ERC-1967 proxies** (MEASURED). Implementations are
upgradeable, so re-resolve before trusting a cached ABI. `census.py totals` does this
automatically.

| Contract | Proxy | Implementation (as of Aug 2026) |
|---|---|---|
| ERC-8004 IdentityRegistry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | `0x7274e874ca62410a93bd8bf61c69d8045e399c02` |
| ERC-8004 ReputationRegistry | `0x8004B663056A597Dffe9eCcC1965A193B7388713` | `0x16e0fa7f7c56b9a767e34b192b51f921be31da34` |
| ERC-8004 ValidationRegistry | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` | `0xdb31f5d9167f8ebc8b30fbbf814c4d297c2d7f99` |
| ERC-8183 AgenticCommerce | `0x0747EEf0706327138c69792bF28Cd525089e4583` | `0xa316fd02827242d537f84730f8a37d0ba5fd351a` |
| USDC (gas token) | `0x3600000000000000000000000000000000000000` | — |

Deployment blocks (MEASURED, binary search on `eth_getCode`): the three ERC-8004
registries at blocks 29,241,340 to 29,241,349, roughly 156 days before Aug 29, 2026.
AgenticCommerce at 33,908,011, roughly 132 days.

**Mainnet contract addresses are not published yet.** Everything above is testnet only.

**Arc's ERC-8004 registries are different deployments from the canonical ones:**

| Chain | IdentityRegistry | ReputationRegistry |
|---|---|---|
| ETH / BSC / Base | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| Arc Testnet | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |

Same `0x8004` vanity prefix, different deployment, different ABI. Arc is its own
reputation silo.

Also on Arc: EURC, USYC (via Teller contract, requires approval), CCTP, Gateway,
StableFX. Full list at https://docs.arc.io/arc/references/contract-addresses.md

## 3.5 Ecosystem infrastructure available on Arc

**Oracles.** Arc joined **Chainlink Scale** (late June 2026), bringing CCIP, Data
Streams, Data Feeds, and Proof of Reserve. Oracle availability is not a constraint. We
still prefer designs that avoid oracles, because an oracle is a trust dependency you
have to defend, not because it is unavailable.

**Data indexers** (per Arc docs): Envio (HyperIndex), Goldsky (Subgraphs, Mirror),
The Graph, thirdweb Insight, Zerion API.

**Node providers:** QuickNode, Chainstack, GetBlock.

**Wallets (testnet partners):** Bron, Exodus, Fireblocks, Hecto Innovation, Ledger,
MetaMask, Privy, Rainbow, Turnkey, Vultisig. Plus Circle's own developer-controlled
and user-controlled wallets.

**Circle platform services:** App Kit (Bridge, Swap, Send, Unified Balance), CCTP,
Gateway, Paymaster / Gas Station (sponsors gas so the app pays, not the agent),
Smart Contract Platform.

**Other Arc-native primitives:** StableFX (enterprise RFQ FX engine with onchain
settlement), USYC (tokenized money market fund, ~$1.6B AUM as of Jan 2026),
built-in FX engine with 24/7 PvP settlement.

---

# 4. The standards

## 4.1 x402

HTTP-native payment protocol using the 402 Payment Required status code.

**Flow:** Agent requests resource, server returns 402 with payment schemes and amount,
agent signs a **gasless EIP-3009 USDC transfer authorization**, agent retries with a
payment header, server forwards to a **facilitator**, facilitator submits the transfer
on-chain and confirms settlement, server returns the resource.

**Payment schemes:**
- `exact` — fixed amount (e.g. $1 to read an article)
- `upto` — usage-based (e.g. LLM token generation)

**Key mechanic:** EIP-3009 (`transferWithAuthorization` / `receiveWithAuthorization`)
separates *authorization* from *paying gas*. The agent signs; a facilitator pays gas
and submits. This is what makes sub-cent agent micropayments viable.

**Governance:** The x402 Foundation launched July 14, 2026 with roughly 40
organizations including Visa, Mastercard, and AWS. The canonical repo moved to the
`x402-foundation` GitHub org.

**SDK language split:** TypeScript ~50%, Python ~29%, Go ~19%.

**MCP integration:** x402 includes MCP payment wrappers and "bazaar" MCP tool
discovery extensions. Cloudflare has a Monetization Gateway selling content and APIs
headlessly over x402.

**Settlement asset:** 99.3% of x402 agent-payment volume settles in USDC.

## 4.2 ERC-8004 (Trustless Agents)

Ratified and live on Ethereum mainnet January 29, 2026. Sits as a *trust layer*
between communication protocols (MCP, A2A) and payment rails (x402).

Three singleton registries per chain:

**IdentityRegistry** — ERC-721 + URIStorage. Every agent is a transferable NFT.
Global identifier is `<eip155:chainId:registryAddress, agentId>`. The `tokenURI`
resolves to an off-chain JSON registration file.

**ReputationRegistry** — client feedback. Only integrity rule: an agent's owner cannot
rate their own agent. **MEASURED: the deployed contract does enforce this.** In 35
rated agents sampled, zero had the owner address among their reviewer set.

**ValidationRegistry** — independent attestations. Pluggable: stake-secured
re-execution, zkML proofs, TEE attestation.

### Arc ABI (MEASURED against the deployed implementations)

Session 1 recorded a `giveFeedback` signature that does not match the deployed
contract. Corrected:

```solidity
// IdentityRegistry (0x7274e874...)
register()                                    // no URI at all
register(string agentURI)
register(string agentURI, tuple[] metadata)
tokenURI(uint256 tokenId) -> string
ownerOf(uint256 tokenId) -> address
setAgentURI(uint256 agentId, string newURI)
getAgentWallet(uint256 agentId) -> address
setAgentWallet(uint256 agentId, address newWallet, uint256 deadline, bytes signature)
getMetadata(uint256 agentId, string metadataKey) -> bytes
setMetadata(uint256 agentId, string metadataKey, bytes metadataValue)

event Registered(uint256 agentId, string agentURI, address owner)
event URIUpdated(uint256 agentId, string newURI, address updatedBy)
event MetadataSet(uint256 agentId, string indexedMetadataKey, string metadataKey, bytes metadataValue)

// ReputationRegistry (0x16e0fa7f...)
giveFeedback(
  uint256 agentId,
  int128  value,
  uint8   valueDecimals,
  string  tag1,
  string  tag2,
  string  endpoint,
  string  feedbackURI,
  bytes32 feedbackHash
)
getClients(uint256 agentId) -> address[]
getLastIndex(uint256 agentId, address clientAddress) -> uint64
readFeedback(uint256 agentId, address clientAddress, uint64 feedbackIndex)
  -> (int128 value, uint8 valueDecimals, string tag1, string tag2, bool isRevoked)
readAllFeedback(uint256 agentId, address[] clientAddresses, string tag1, string tag2, bool includeRevoked)
  -> (address[] clients, uint64[] feedbackIndexes, int128[] values, uint8[] valueDecimals,
      string[] tag1s, string[] tag2s, bool[] revokedStatuses)
getSummary(uint256 agentId, address[] clientAddresses, string tag1, string tag2)
  -> (uint64 count, int128 summaryValue, uint8 summaryValueDecimals)
revokeFeedback(uint256 agentId, uint64 feedbackIndex)
appendResponse(uint256 agentId, address clientAddress, uint64 feedbackIndex, string responseURI, bytes32 responseHash)

event NewFeedback(uint256 agentId, address clientAddress, uint64 feedbackIndex,
                  int128 value, uint8 valueDecimals, string indexedTag1, string tag1,
                  string tag2, string endpoint, string feedbackURI, bytes32 feedbackHash)

// ValidationRegistry (0xdb31f5d9...)
validationRequest(address validatorAddress, uint256 agentId, string requestURI, bytes32 requestHash)
validationResponse(bytes32 requestHash, uint8 response, string responseURI, bytes32 responseHash, string tag)
getValidationStatus(bytes32 requestHash)
getAgentValidations(uint256 agentId)
getValidatorRequests(address validatorAddress)
getSummary(uint256 agentId, address[] validatorAddresses, string tag)
```

**Notes that matter:**

- `getClients` and `readAllFeedback` mean the entire reputation graph is readable by
  plain `eth_call`. No event scanning required, which is why the reputation analysis in
  `tools/arc-census` works against the rate-limited public RPC.
- `register()` with no arguments exists, so an agent can be minted with no URI at all.
- `appendResponse` gives a rated agent a right of reply. Nobody uses it.
- Validation response: 100 = passed, 0 = failed. Owner requests, validator responds.
- **The ValidationRegistry is deployed and in use on Arc testnet** (110,222
  transactions, MEASURED). The July 2026 empirical study found no confirmed mainnet
  deployment on Ethereum, BSC, or Base and excluded it from scope. This dataset does
  not exist anywhere in the literature.

## 4.3 ERC-8183 (Agentic Commerce)

Draft EIP from February 2026. Authors include Davide Crapis (Ethereum Foundation dAI
team) and contributors from Virtuals Protocol.

A **Job** primitive with escrowed budget, three roles, and a state machine.

**Roles:** Client (creates and funds), Provider (does the work), Evaluator (alone may
mark completed).

**States:** `Open → Funded → Submitted → Terminal` where Terminal is Completed,
Rejected, or Expired.

### Arc reference implementation ABI (MEASURED)

```solidity
createJob(address provider, address evaluator, uint256 expiredAt, string description, address hook)
  -> uint256 jobId
setBudget(uint256 jobId, uint256 amount, bytes optParams)
setProvider(uint256 jobId, address provider_)
fund(uint256 jobId, bytes optParams)
submit(uint256 jobId, bytes32 deliverable, bytes optParams)
complete(uint256 jobId, bytes32 reason, bytes optParams)
reject(uint256 jobId, bytes32 reason, bytes optParams)
claimRefund(uint256 jobId)

jobs(uint256) -> (uint256 id, address client, address provider, address evaluator,
                  string description, uint256 budget, uint256 expiredAt,
                  uint8 status, address hook)
jobCounter() -> uint256
jobHasBudget(uint256 jobId) -> bool

// admin only
setHookWhitelist(address hook, bool status)
whitelistedHooks(address) -> bool
setEvaluatorFee(uint256 feeBP_)
setPlatformFee(uint256 feeBP_, address treasury_)
evaluatorFeeBP() -> uint256
platformFeeBP() -> uint256

event JobCreated(uint256 jobId, address client, address provider, address evaluator,
                 uint256 expiredAt, address hook)
event JobSubmitted(uint256 jobId, address provider, bytes32 deliverable)
event JobCompleted(uint256 jobId, address evaluator, bytes32 reason)
event EvaluatorFeePaid(uint256 jobId, address evaluator, uint256 amount)
event PaymentReleased(uint256 jobId, address provider, uint256 amount)
```

Status enum order: `Open, Funded, Submitted, Completed, Rejected, Expired`.

### Three things that matter, all three now resolved

**1. `commitmentRef` does not exist. (O7 RESOLVED, negative.)**

Session 1 recorded that a field originally named `intent` was renamed `commitmentRef`
during spec review, preserving its cryptographic binding property, and flagged as
UNVERIFIED whether it landed in the Arc deployment.

It did not. The verified implementation source contains **zero** occurrences of
`commitmentRef` and zero of `intent`. There is no commitment field on the job struct.

**Workable substitute using only what exists.** The lifecycle already provides three
write slots at exactly the right moments:

| Slot | Type | Written by | When | Use for |
|---|---|---|---|---|
| `description` | string | client | `createJob`, before anything happens | **purpose hash** |
| `deliverable` | bytes32 | provider | `submit` | response hash |
| `reason` | bytes32 | evaluator | `complete` / `reject` | verdict hash |

`description` is set at creation and never mutated. That is a genuine pre-commitment
slot. We need neither `commitmentRef` nor a new contract.

**2. Hooks are whitelist-gated. (New finding.)**

`setHookWhitelist(address, bool)` is restricted to `ADMIN_ROLE`. A hook must be
whitelisted before it can be attached to a job. **We cannot deploy an IACPHook that
enforces evaluator independence or evidence-backed feedback.** §11 item 7 is therefore
a proposal to Circle, not a build.

MEASURED: `hook == address(0)` in **120 of 120** sampled jobs. 100% non-adoption, which
is unsurprising given nobody can adopt it.

**3. Evaluator fees exist but are set to zero. (Correction.)**

Session 1 said the economics of funding evaluation from escrow were "already a
parameter, not something we would have to invent." True, but:

```
evaluatorFeeBP() = 0
platformFeeBP()  = 0
platformTreasury = 0xcbe5b97a069be3e4b5398663790731fb76ab620d
paymentToken     = 0x3600000000000000000000000000000000000000  (USDC)
```

Only `ADMIN_ROLE` can change them. **Funding evaluation out of escrow is not available
to us on the deployed contract.** This matters for §11 item 1 (peer prediction), which
assumed evaluators could be paid from escrow.

## 4.4 AP2 (Agent Payments Protocol)

Google's standard, announced September 16, 2025, with 60+ launch partners including
Mastercard, PayPal, Coinbase, American Express, Salesforce. Treats stablecoin rails as
first-class alongside cards.

Three signed **Mandates** carried as W3C Verifiable Credentials (JSON-LD, ECDSA over
P-256 or stronger, SHA-256 integrity):

- **Intent Mandate** — the user's natural-language request, an optional NLP-summarized
  "prompt playback" string, hard constraints (max price, specs, expiry/TTL, allowed
  merchants), and the agent's identity reference. Signed by the user. Critical for
  human-not-present flows.
- **Cart Mandate** — merchant-generated, binds specific SKU, price, tax, shipping.
  Signed by the user with a hardware-backed device key in human-present flows.
- **Payment Mandate** — authorizes payment against a specific instrument, shared with
  the credential provider, networks, and processor.

Mandates exist in Open (constraints and goals, pre-cart) and Closed (authorization
bound to a finalized checkout) states.

**Why this matters to us:** AP2 is the "declare before" half of our idea, already
built and institutionally backed. It captures intent as a signed, verifiable artifact
for the purpose of authorization and liability. **It never checks afterward whether the
stated purpose was served.** That is the gap.

AP2's separation of hard constraints from the natural-language request is direct
precedent for the hard/soft split in O1.

## 4.5 How the standards stack

```
Communication:  MCP (agent↔tool), A2A (agent↔agent)
Trust:          ERC-8004 (who is this agent, can it be trusted)
Commerce:       ERC-8183 (how do we structure, evaluate, and settle the work)
Authorization:  AP2 (what did the user authorize)
Payment:        x402 (how does money move)
Asset:          USDC
Settlement:     Arc / Base / Solana / Algorand
```

Discovery layer: x402 Bazaar (Coinbase CDP), plus community alternatives.

---

# 5. What Circle's own tutorials teach, and what that produced

Both Arc agent quickstarts are complete runnable scripts (TypeScript + Python, Circle
Wallets + raw viem tabs). They automate **the transactions**. Registration, feedback,
validation, and the full 8183 job lifecycle are all `npm run start`.

They do **not** automate correctness. Session 2 measured the consequences.

| # | Tutorial pattern | Measured outcome on Arc testnet |
|---|---|---|
| 1 | Example metadata is not ERC-8004 compliant: `name`, `description`, `image`, `agent_type`, `capabilities`, `version`, with no `type`, no `services` array, no `registrations` array, no x402 flag. Docs say the fields are "application-defined." | **0 of 250** sampled agents have a `services` array. 0 have `registrations`. 0 mention x402 or MCP. |
| 2 | Everyone is offered the same IPFS URI (`bafkreibdi66...`) so they can skip uploading. | 3 of 250 point at that exact CID. A further 4 point at fabricated CIDs that are hex padded to look valid. |
| 3 | Reputation is demonstrated as self-dealing: create two wallets you control, have the second write a hardcoded `score: 95` about the first. | Owner-rates-own-agent is **0**, because the contract blocks it. But **959 distinct reviewer addresses produced 1,008 reviews**, top reviewer at 0.5%. Almost every reviewer rates once and vanishes. That is the two-wallet pattern at scale. |
| 4 | Evidence fields passed empty: `feedbackURI` as `""`, `feedbackHash` as `keccak256(tag)`. | The `endpoint`, `feedbackURI`, and `feedbackHash` slots exist and go unused. |
| 5 | "The client also acts as the evaluator" in the 8183 quickstart. | **`evaluator == client` in 67.5%** of 120 sampled jobs. |
| 6 | `hook` passed as `address(0)`. | **100%** of sampled jobs. Also structurally enforced (§4.3). |

**Implication:** the plumbing value of a "launcher" product is gone, Circle collapsed
it into one command. The *correctness* value is wide open, and we can now show that
with numbers rather than assertion.

---

# 6. The measured state of Arc (session 2)

Full detail in `docs/03-session-02-census-findings.md`. Summary:

| Registry | Measure | Value |
|---|---|---|
| IdentityRegistry | Transfer events | 887,911 |
| IdentityRegistry | Highest agent ID | 888,262 |
| IdentityRegistry | Distinct holders | 47,215 |
| ReputationRegistry | Transactions | 18,972,296 |
| ValidationRegistry | Transactions | 110,222 |
| AgenticCommerce | Transactions | 600,477 |
| AgenticCommerce | `jobCounter()` | 182,367 |

For comparison, the July 2026 study counted roughly 170,000 agents across Ethereum,
BSC, and Base combined. **Arc testnet alone has about five times that.**

Uniform random sample of 250 agents (seed 7):

| Result | Count | Share |
|---|---|---|
| Inline `data:` template metadata | 238 | 95.2% |
| `ipfs://` | 7 | 2.8% |
| `https://` | 4 | 1.6% |
| No URI set | 1 | 0.4% |
| Declares anything resembling a service endpoint | 4 | 1.6% |
| **Reachable service endpoint** | **0** | **0%** |

All four declared endpoints fail: three point at `arc-agent.example.com` (the RFC 2606
reserved domain), one returns HTTP 502. Rule of three puts the 95% upper bound on the
true reachability rate at 1.2%, so an upper bound of roughly 10,600 reachable agents
chain-wide and realistically far fewer. The July 2026 study found 3% on Ethereum, 4% on
BSC, 15% on Base. **Arc is materially worse than all three.**

Name templates account for 215 of 238 parsed documents, about 90%: `Agent-XXXXXX`
(109), `Trader-XXXXXX` (56), `Bridge-XXXXXX` (50).

**Ownership concentration** (full distribution, all 47,444 holders, not a sample):
Gini **0.8879**, the highest of any chain measured, against 0.733 on Ethereum, 0.708
on Base, and 0.134 on BSC. The shape differs from Ethereum's: the top 1% holds only
25.5% and the largest holder has 904 agents (0.1%). What drives the coefficient is
**~2,998 wallets each holding between 100 and 499 agents, together 79.4% of the entire
population**, alongside 31,367 wallets holding exactly one. A flat farm rather than a
few whales.

Reputation, 2,295 feedback records decoded from 35 rated agents:

- **`valueDecimals` is used inconsistently within the same registry**: 1,742 records at
  2 decimals, 549 at 0, 4 at 1. A raw value of `85` means 0.85 to one writer and 85 to
  another. This is the commensurability failure (C1, §7.1) measured rather than argued.
- 316 distinct free-form tags.
- Normalized values span 9.2 to 98.0. No negatives, nothing above 100.

**Method note.** An earlier pass reported 48 of 250 agents (19.2%) with no URI set.
That was a measurement error: an ad-hoc script swallowed RPC rate-limit failures as
empty results. Re-run through `arc-census`, which retries with backoff and
distinguishes a contract revert from a transport failure, the figure is 1 of 250. Keep
this in mind when scaling the sample: silent transport failure looks exactly like a
finding.

---

# 7. Research findings

## 7.1 The ERC-8004 empirical study

**"Can Trustless Agents Be Trusted? An Empirical Study of the ERC-8004 Decentralized
AI Agent Ecosystem"** — arXiv:2606.26028v2, July 8, 2026. Xiong (Imperial), Li (Ohio
State), Wei (Bristol), Wang (CSIRO), Knottenbelt (Imperial), Wang (Manchester).

Covers Ethereum, BSC, and Base from deployment through May 13, 2026. ~170k registered
agents, ~150k feedback records. **The single most useful document found.**

### Identity findings

| Chain | Total agents | Valid reg file | No URI set | Valid + live service endpoint |
|---|---|---|---|---|
| Ethereum | 32,343 | 29.4% | 53% | **3%** |
| BSC | 90,145 | 83.4% | 9% | **4%** |
| Base | 50,985 | 26.9% | 37% | **15%** |
| **Arc (ours)** | **~888,000** | **0%** | **0.4%** | **0%** |

- Ownership concentration: Gini 0.733 (ETH), 0.708 (Base), 0.134 (BSC). Top 1% of ETH
  wallets own 58.5% of agents. **Arc MEASURED: Gini 0.8879, the highest of any chain
  measured, but with a different shape. Top 1% holds only 25.5% and the largest holder
  has 904 agents (0.1%). What drives it is ~3,000 wallets each holding 100 to 499
  agents, together 79.4% of the population. A flat farm, not whales.**
- On Ethereum, 2.6% of registration transactions (batch) produced 48.3% of all agents.
  **Not yet measured for Arc**; needs transaction-level scanning.
- Activation is near-instant or never: 92-93% of later-activated agents set their URI
  within one day.
- Service types: BSC is ~70% plain Web; Base has the strongest agent-native presence
  (MCP + A2A ≈ half of declarations); Ethereum is mixed. **Arc: zero declarations.**

### Reputation findings

Four necessary conditions for a trust signal, none of which the registry meets:

- **C1 Commensurability** — no shared scale. `value` is a signed integer with a
  `valueDecimals` field. Tags are free-form. Identical tags use incompatible scales.
  Base had 764 records above 100 and 20 below zero. **Confirmed on Arc: three
  different `valueDecimals` values in use simultaneously.**
- **C2 Robustness** — the aggregate is an unweighted mean; a single input can move it.
  No safe threshold exists.
- **C3 Groundedness** — feedback is not tied to verifiable interactions. No stake, no
  registration, no prior interaction required.
- **C4 Economic soundness** — median cost to fabricate or destroy a reputation:
  **$0.055 (ETH), $0.0042 (BSC), $0.0027 (Base)**. At ~0.006 USDC/tx, Arc is roughly
  Ethereum's cost and more than double Base's. Still trivially cheap.

Manipulation in the wild:

| Chain | Sybil-flagged reviewers | Rated agents affected | Agents left with zero valid feedback after removal |
|---|---|---|---|
| Ethereum | 73.5% | 26.4% | 15.8% |
| BSC | 59.2% | 81.4% | 77.9% |
| Base | 90.6% | 96.2% | 86.8% |

Cross-chain: only 629 of 173,441 agents (0.4%) declare registration on 2+ mainnets, and
their scores are **uncorrelated across chains** (Spearman ρ=0.05, p=0.56 for BSC-Base;
ρ=0.14, p=0.48 for ETH-Base). Each chain is an isolated reputation silo.

**Still to read:** Section 8 (Recommendations for Protocol Designers). If they already
propose payment-gated feedback, our build becomes "reference implementation of a
published recommendation," which is a stronger frame.

## 7.2 Peer prediction (information elicitation without verification)

The academic answer to "who judges the judge." Mechanism-design work on eliciting
honest reports about subjective things where no ground truth exists and spot-checking
is impossible.

**Core mechanism:** score a reporter not on matching an authority, but on how
predictive their report is of what other independent reporters said. Under the right
construction, truth-telling is a strict Bayes-Nash equilibrium; "strongly truthful"
variants make it the highest-paying symmetric equilibrium.

**Foundational:** Miller, Resnick & Zeckhauser (2005), *Eliciting Informative Feedback:
The Peer-Prediction Method*. Prelec (2004), *Bayesian Truth Serum*, which notably does
not require a common prior.

**Modern / LLM-relevant:** arXiv:2601.20299 (January 28, 2026), *Truthfulness Despite
Weak Supervision: Evaluating and Training LLMs Using Peer Prediction* (Qiu et al.).
Applies peer prediction to LLM evaluation using mutual predictability, with theoretical
guarantees and empirical validation up to 405B-parameter models.

**Known failure modes, read before relying on any of this:**

- **Constant-report collusion is also an equilibrium.** If every evaluator always says
  "pass," they agree perfectly and all get paid. Multi-task mechanisms are the standard
  defense but are a defense, not a proof.
- **Gao et al. (2016), *Incentivizing Evaluation via Limited Access to Ground Truth:
  Peer-Prediction Makes Things Worse.*** Partial ground truth access can make outcomes
  worse. Directly relevant: our setting has partial ground truth, since some purposes
  are machine-checkable and some are not.
- **Measurement integrity is a separate axis from strategic robustness.**
  arXiv:2108.05521, *Measurement Integrity in Peer Prediction: A Peer Assessment Case
  Study.* A mechanism can be provably truthful and still produce measurements that do
  not track quality. Most theory optimizes robustness and ignores this. **For our use
  case, measurement integrity is what we actually care about.**

**Other references:** Schoenebeck et al. 2020 (multi-task, variational approach),
Chen et al. 2024 (comparison data, bonus-penalty), arXiv:2503.16280 (peer prediction
with more signals than reports), arXiv:2506.02259 (stochastically dominant peer
prediction).

**Status: essentially zero on-chain deployment of any of this.** Note also that the
Arc 8183 contract's evaluator fee is zeroed and admin-gated (§4.3), so the economic
half cannot be built on it as deployed.

## 7.3 Agent audit trails (the "record after" half)

A 2026 category driven by EU AI Act obligations (Regulation 2024/1689; Article 5
prohibitions and Article 4 AI-literacy requirements effective August 2, 2026).

- IETF draft `draft-sharif-agent-audit-trail-00` — a standard JSON logging format with
  SHA-256 hash chaining per RFC 8785 and optional ECDSA signatures. Maps to SOC 2,
  ISO/IEC 42001, PCI DSS v4.0.1.
- Multiple commercial vendors selling tamper-evident agent decision records.

Their framing of the questions an audit trail must answer: who authorized this, what
context did the agent have, what did it decide, was that consistent with policy.

**Note the missing fifth question: did it work.**

## 7.4 The gap, stated precisely

AP2 built the declaration. Audit-trail vendors built the recording. **Nobody joins
them.** AP2 mandates are authorization artifacts used for liability and chargebacks;
the protocol never grades the outcome against the stated intent. Audit trails record
what happened but have no declared purpose to grade against.

Closing that loop is the idea. No prior art found.

**Why the loop closure makes subjective evaluation tractable:** "was this good" has no
fixed referent. But if the agent writes the rubric *before* it knows the outcome,
evaluation becomes "did it match what you said," which is far better-posed and
something an LLM can answer consistently.

---

# 8. Competitive landscape

## 8.1 x402 quality / monitoring / discovery (all on Base, none on Arc)

| Project | What it does | Metrics used |
|---|---|---|
| **x402 Bazaar** (Coinbase CDP) | Official discovery layer. Searchable by intent, MCP server, listed as an AWS Bedrock AgentCore gateway target exposing 10,000+ paid MCP tools. Self-described as "Yahoo search stage." | Capability, price, schema |
| **x402.fuchss.app** | 25,000+ endpoints monitored 24/7. Trust scores sold pay-per-call from $0.005. Free top-25 leaderboard. MCP tools. | Uptime, 402-envelope compliance, latency, age, on-chain settlement activity, price stability |
| **ScoutScore** | 24 days monitoring 1,700+ domains. Reported avg fidelity 52/100, 80.6% uptime, a 10,658-service spam cluster. SDK. | Reliability, red flags |
| **402.ad** | 17,557 MCP servers + x402 APIs. "Describe the job, get ranked results." 5-stage pipeline, 15-min health checks. | Pricing, schemas, auth, install steps, health |
| **x402-list** | 470 services / 2,133 endpoints, 1,880 checks/hour. Open machine-readable directory. | Uptime |
| **x402station** | Analytics + UI, 200+ APIs. Sells a $1 USDC autonomous "Verified" badge. | Probe frequency ≥20/7d, uptime ≥95%, no critical failures, P99 ≤5000ms, price sanity $0.0001–$5 |
| **Analytix402** | Monitoring + security scanning | SSL, headers, error handling, payment verification, threat detection |
| **Agentic Resource Radar** | Verified agent reviews + reliability. Reviews only count when backed by verified x402 usage. | Freshness, speed, liveness, submitted reviews |
| **x402Scout** (`rplryan/x402-discovery-mcp`) | Community Bazaar + autonomous routing. Fee: max($0.003, 2.5% of downstream value). | Quality signals, facilitator compat, ERC-8004 trust scoring |
| **Onyx Bazaar** | Free leaderboard of paid x402 services via CDP discovery API, refreshed every 15 min | Volume, unique payers, recency, price |
| **x402scan** | x402 ecosystem explorer: transactions, sellers, origins, resources | Transaction data |

**Every single one measures liveness. None measure whether the answer was good.**

## 8.2 ERC-8004 explorers

| Project | Coverage |
|---|---|
| **QuickNode ERC-8004 Explorer** (erc-8004.quicknode.com) | Search by agent ID/address across Ethereum, Base, BNB Chain, Avalanche, Mantle. Public composite scoring formula, replayable against raw events. REST API paid per request in USDC over x402, no API key. JSON-RPC across 26 EVM networks. |
| **AgentZone** | ERC-8004 identity + x402 payment history + reputation + live service status, Base and Arbitrum |
| **8004scan.io** | Agent reputation and validation history |
| Various trust-scoring projects | One indexes 150,000+ agents across 12 EVM chains + Solana |

## 8.3 What we ruled out and why

| Idea | Killed by | Reasoning |
|---|---|---|
| **Arc agent indexer / analytics** | QuickNode | Their ERC-8004 Explorer is essentially our v0 spec, already shipped, by a company with the RPC pipeline and the incentive. Adding Arc is a config change for them. |
| **Settlement-grounded reputation contract** | Adoption problem | Only useful if agents choose to write to it instead of the canonical registry. On a chain whose agent population is 888k bots, that is a protocol nobody uses. Survives as an off-chain derivation. |
| **Agent launcher / deployer with guardrails** | Cloudflare, Coinbase, Circle, and Circle's own quickstarts | Cloudflare Wallets (Aug 4, 2026) ship Account/Virtual wallet tiers with allowances, allow-lists, max transaction size, human override. Coinbase shipped agent wallets June 2026. Arc has ERC-4337/7702 native. OmniAgentPay won a hackathon on this in January and the window closed by August. |
| **Routing / recommendation layer** | Bazaar + x402Scout + 402.ad | Built at least three times, including by Coinbase. |
| **Deterministic evaluator only** | Too narrow | Only works on schema-checkable outputs. Survives as the hard-constraint half of the purpose document. |
| **ERC-8183 hook contract** | **Admin whitelist (MEASURED)** | Not a build decision any more. `setHookWhitelist` is `ADMIN_ROLE` only. This is now a proposal to Circle. |

## 8.4 Where that leaves the differentiator

Everyone measures whether agentic services are up. Nobody measures whether they are
right. Nobody measures variance under paraphrase. And every project above is on Base.

Arc has none of them, and session 2 explains why: **there is nothing on Arc worth
monitoring.**

---

# 9. Design decisions

| # | Decision | Rationale | Status |
|---|---|---|---|
| D1 | Build a **mystery shopper**, not infrastructure | Solo dev cannot compete on indexing/monitoring. A shopper is a cron job plus a website: no adoption requirement, no uptime obligation, no support burden. Means something with n=1. | Holds |
| D2 | **Purpose declared before, graded after** | Closes the loop AP2 and audit vendors each leave open. Makes subjective evaluation tractable by fixing the referent before the outcome is known. | Holds |
| D3 | **Swarm of phrasing variations**, not single-shot | Disambiguates "bad service" from "bad query." Without it every score is contestable on exactly that ground. Also yields variance, which nobody measures. | Holds |
| D4 | Grade in **words, not just numbers** | ERC-8004's numeric field is where semantic collapse happens (C1). A structured purpose + verdict + evidence is strictly more information than `95`, degrades gracefully into a number, and is LLM-ingestible. | Strengthened by §6 |
| D5 | Also produce **query optimization insights** | Turns the project from antagonist into something useful to sellers and buyers at once. | Holds |
| D6 | **Wrap, do not compete with, Bazaar** | Produce the signal the routers lack instead of being the twelfth router. | Holds |
| D7 | **Testnet is the feature, not the limitation** | Only place you can spawn synthetic buyers, spend freely, send malformed requests, run adversarial agents. | Holds, but the Sept 16 deadline was wrong (§2.1) |
| D8 | **Skip peer prediction for v1** | Needs multiple evaluators and real stakes. Note it as the next step. | Holds, and escrow-funded evaluation is now known to be unavailable (§4.3) |
| D9 | **No routing in v1** | Variance data makes the case on its own. Routing needs outcome data to exist first. | Holds |
| D10 | Prefer designs that **avoid oracles** | Not availability. An oracle is a trust dependency you have to defend in a pitch. | Holds |
| D11 | **Depth over breadth** | 20 services deeply, not 25,000 shallowly. | Holds, but Arc has 0 shoppable services (§6) |
| D12 | **Publish everything** | LLM verdicts cannot be trustless and should not pretend to be. Contestable and transparent beats fake determinism. | Holds |
| D13 | Evaluate at **session/task granularity**, not per-request | An LLM eval per micropayment costs more than the payment. | Holds |
| **D14** | **Deploy our own calibration services** | Engineered quality profiles give known ground truth, the only way to demonstrate measurement integrity (§7.2). Also required on Arc, where there is nothing else to shop. | New, session 2 |
| **D15** | **Blind the evaluator** | Judge sees neither service identity, price, nor which phrasing produced the response. Otherwise halo effects contaminate everything and "does price predict quality" becomes unanswerable from our own data. | New, session 2 |
| **D16** | **Bind purpose via `description`, not a new field** | `commitmentRef` does not exist. `description` is set at `createJob` and never mutated, which is a genuine pre-commitment slot. No new contract needed. | New, session 2 |

---

# 10. Open decisions

| # | Question | Notes |
|---|---|---|
| O1 | **What does the purpose document actually look like?** | The hardest part and the one everything downstream depends on. Session 2 direction: split into a **hard-constraint block** (machine-checkable, deterministic, mirrors AP2 Intent Mandate constraints and OmniAgentPay spending guards) and a **soft-purpose block** (LLM-graded). Scheduled for session 3. |
| O2 | **Do we name the services we evaluate?** | Naming makes findings concrete but means publishing negative results about identifiable operators. **Note: this now also applies to the census.** Naming the 888k farmed registrations is not a concern; naming a real operator later is. Unresolved. |
| O3 | **Scope: how many services, purposes, phrasings, repeats?** | First concrete number: 6 × 4 × 5 × 3 = 360 evaluations, roughly $7 of inference. |
| O4 | **What does a single result record contain?** | Schema in `docs/02-build-plan.md` §3. Verdict is a separate entity from attempt, so multiple judges can grade the same attempt later. |
| O5 | **Business model** | Pay-to-be-evaluated carries the credit-rating-agency conflict. Works for x402station because their criteria are mechanical. The moment the rating is a quality judgment, being paid by the rated party compromises it. Grant-funded or free is more credible. Does not need answering to start. |
| O6 | **Who writes the purpose, and how do we stop it being gamed?** | If an agent writes its own purpose it writes an easy one. Partial fixes: bind before outcome is knowable, have someone other than the agent judge, and track whether stated purposes get vaguer over time. That drift metric may be the most interesting signal in the system. |
| ~~O7~~ | ~~Does `commitmentRef` exist in the Arc-deployed 8183 contract?~~ | **RESOLVED, negative. See §4.3.** |
| O8 | **Which evaluator model(s)?** | Single model for v1 (D8), but which, and with what rubric. Scheduled for session 4. |
| **O9** | **Census first, or shopper first?** | New. The census is faster, publishable, unblocked, and is the argument for the shopper. Recommendation: census first. |

---

# 11. Known risks

| Risk | Mitigation |
|---|---|
| **No shoppable services on Arc.** MEASURED: 0 of 250 agents reachable. | Deploy calibration services (D14). Shop Base, record on Arc. This was the top unlisted risk in session 1 and it materialized. |
| **The judge is not self-consistent.** Untested. Kills the project, not just the plan. | Phase 0 of the build plan: 4 purposes × 6 hand-written mock responses × 3 runs, no blockchain. Cheap, and it goes first. |
| **Silent transport failure looks like a finding.** Already bit us once (§6 method note). | All sampling goes through `arc-census`, which retries with backoff and separates a revert from a network failure. Never use ad-hoc scripts for numbers you intend to publish. |
| **Cost multiplication.** Variations × repeats × services is combinatorial. | Free on testnet. Does not transfer to mainnet unchanged, sample rather than sweep. |
| **Overfitting to our own voice.** If one generator writes all query variations, "optimal phrasing" may just mean "phrasing our generator produces." | Vary the generator. Multiple models plus hand-seeded variations. Build this in from the start or every finding is an artifact of our prompt style. |
| **Agent grades its own homework.** | See O6. |
| **LLM verdicts are not reproducible** and cannot honestly live on-chain. | Verdict hash + purpose hash + evidence URI on-chain; judging off-chain; publish rubric and full transcript so it is contestable. |
| **Goodharting.** Agents learn to write trivially satisfiable purposes. | Bind purpose before outcome; third-party judging; track specificity drift. |
| **Testnet USDC is worthless**, so the economic half of peer prediction cannot be tested. | Be upfront. Testnet tests mechanics and measurement integrity. The incentive question waits for mainnet or simulation. Also note `evaluatorFeeBP = 0` and admin-gated (§4.3). |
| **Circle may ship this themselves.** | Real. Their H2 roadmap is agent-earning, and the September 16 launch includes AI-powered app and contract building tools. Speed and honest publication are the only defenses. |

---

# 12. Future work (post-v1)

Roughly in order of value.

1. **The census paper.** "The State of ERC-8004 on Arc." Publishable now off data
   already collected. Covers a chain nobody has measured, and includes 110,222
   ValidationRegistry transactions that do not exist in the literature because the
   July 2026 study found no mainnet deployment anywhere.
2. **Peer prediction evaluator layer.** Multiple independent evaluators, scored by a
   multi-task peer prediction rule rather than by agreeing with a designated judge.
   Blocked on funding, since escrow evaluator fees are zeroed and admin-gated.
3. **Failure taxonomy.** What actually goes wrong when agents pay for things: paid and
   got nothing, wrong response shape, silent quality degradation, timeout after
   settlement. Calibration services (D14) seed this with designed failures.
4. **Coaching loop.** Feed purpose-quality feedback back to agents. Do agents that
   receive it write better-specified purposes over time, and does better specification
   correlate with higher completion rates? Cheap experiment, nobody has run it.
5. **Does price predict quality?** Bazaar shows cost. Nobody knows. Requires D15
   blinding to answer honestly.
6. **Substitutability.** Two services claiming the same capability: do they return
   equivalent results for the same purpose? What routing eventually needs.
7. **Retry economics.** If three extra calls with better phrasing beats switching
   providers, that is an actionable number. Arithmetic over our logs.
8. **ERC-8183 hook proposal to Circle.** Enforce evaluator ≠ client, evidence-backed
   feedback, reputation writes gated on Terminal jobs. **Not a build**, because hooks
   are admin-whitelisted. Write it as a proposal with the 67.5% and 100% numbers
   attached.
9. **Compliant metadata generator.** A weekend utility producing spec-valid ERC-8004
   registration files with real `type`, `services`, and `registrations` fields. Fixes a
   problem now measured at 100% failure.
10. **Settlement-grounded reputation as an off-chain derived score.** Computed rather
    than enforced. Zero adoption required.
11. **Cross-chain comparison.** Same methodology on Base, where the service population
    is large, versus Arc. Promoted from future work to the v1 spine (§6).
12. **Batch-registration and funding-graph analysis on Arc.** Concentration is done
    (§6). What remains is whether the ~3,000 mid-size farming wallets are one operator
    or many, which ownership data cannot separate. Needs the funding graph.

---

# 13. Reading list

## Must read
- **arXiv:2606.26028v2** — *Can Trustless Agents Be Trusted?* Especially §8
  Recommendations for Protocol Designers. https://arxiv.org/html/2606.26028
- **arXiv:2108.05521** — *Measurement Integrity in Peer Prediction.* The closest thing
  to a warning label on this whole plan.
- **arXiv:2601.20299** — *Truthfulness Despite Weak Supervision: Evaluating and
  Training LLMs Using Peer Prediction.*
- **Gao et al. 2016** — *Incentivizing Evaluation via Limited Access to Ground Truth:
  Peer-Prediction Makes Things Worse.*
- ERC-8183 spec: https://eips.ethereum.org/EIPS/eip-8183, especially the hook
  interface (IACPHook).

## Primary docs
- Arc docs index: https://docs.arc.io/llms.txt
- Register an AI agent: https://docs.arc.io/arc/tutorials/register-your-first-ai-agent.md
- Create an ERC-8183 job: https://docs.arc.io/arc/tutorials/create-your-first-erc-8183-job.md
- Arc contract addresses: https://docs.arc.io/arc/references/contract-addresses.md
- Arc EVM differences: https://docs.arc.io/arc/references/evm-differences.md
- x402 spec: https://github.com/coinbase/x402 (canonical repo now under `x402-foundation`)
- x402 Bazaar: https://docs.cdp.coinbase.com/x402/bazaar
- AP2 spec: https://ap2-protocol.org/specification/
- ERC-8004 contracts: https://github.com/erc-8004/erc-8004-contracts
- Circle Q2 2026 results: https://www.circle.com/pressroom/circle-reports-second-quarter-2026-results
- Circle 2026 product vision: https://www.circle.com/blog/building-the-internet-financial-system-circles-product-vision-for-2026

## Landscape
- `Merit-Systems/awesome-x402`
- `sudeepb02/awesome-erc8004`
- Ethereum Magicians ERC-8183 thread: https://ethereum-magicians.org/t/erc-8183-agentic-commerce/27902
- Past Arc hackathon projects: https://lablab.ai/event/agentic-commerce-on-arc

---

# 14. Session log

## Session 1 — August 29, 2026

Full landscape research. Started from "what can we demo on Arc to get noticed by
Circle," converged on the mystery shopper.

Path taken and what killed each idea:

1. **Settlement-grounded reputation contract** → adoption problem
2. **Arc agent indexer** → QuickNode ERC-8004 Explorer already ships it
3. **Agent launcher with guardrails** → Cloudflare/Coinbase/Circle own the wallet tier;
   Circle's quickstarts own the plumbing
4. **Deterministic evaluator + 8183 hook** → too narrow, but survives as future work
5. **Purpose declaration + outcome evaluation** → no prior art found, kept
6. **Routing / recommendation** → Bazaar, x402Scout, 402.ad already built it
7. **Mystery shopper** → landed here

Killing three ideas on evidence was the most valuable part of the session.

## Session 2 — August 29 to 30, 2026

Moved from research to measurement. Built `tools/arc-census` and ran it against Arc
testnet.

What was established:

- **No hackathon is scheduled** around mainnet launch (§2.5). The Sept 16 deadline was
  a misreading; testnet persists past mainnet (§2.1).
- **Wrote the build plan** (`docs/02-build-plan.md`): architecture, four phases, a
  twelve-session roadmap, data model, and UI direction. Key structural choice is that
  the measurement core has no blockchain dependency and can be validated standalone.
- **Ran the census** (§6). Arc has ~888k agents and zero reachable service endpoints in
  250 samples. The supply risk that was missing from session 1's risk table turned out
  to be the dominant one, and it materialized.
- **Resolved O7 negative**, found hooks are admin-whitelisted, found evaluator fees are
  zeroed, corrected the `giveFeedback` ABI, and measured 67.5% evaluator collapse
  (§4.2, §4.3).
- **Made one measurement error and caught it** (§6 method note). Worth remembering.
- **Published the repo**: github.com/wilwixqa1/arc-agent-evaluation, MIT.

The most valuable output was not the plan, it was discovering that the plan's premise
was wrong before building on it. Keep measuring before designing.

### Next actions

- [ ] Decide O9: census paper first, or shopper first. Recommendation: census.
- [ ] Get a keyed RPC provider (QuickNode or Chainstack). Scales the agent sample from
      250 to 3,000 and makes confidence intervals publication-grade.
- [x] Agent concentration analysis on Arc. Done: Gini 0.8879, ~3,000 wallets holding
      100-499 agents account for 79.4%. See §6 and `docs/03`.
- [ ] Funding-graph analysis: are the ~3,000 farming wallets one operator or many?
- [ ] Enumerate the Base x402 service population before committing to the Base pivot.
- [ ] Read arXiv:2606.26028 §8.
- [ ] Read arXiv:2108.05521.
- [ ] Draft the purpose document schema, hard/soft split (O1), session 3.
- [ ] Evaluator rubric, blinding protocol, and the Phase 0 judge reliability test
      (O8), session 4.
- [ ] Run the Arc quickstarts end to end to get hands on the chain.
