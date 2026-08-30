# Arc Mystery Shopper — Build Plan and Session Roadmap

**Companion to:** the project context file (source of truth for research and decisions)
**Created:** August 29, 2026
**Owner:** Will Wendt
**Assumption:** solo developer, roughly 6 to 10 focused hours per week

---

## 0. Planning premises

Three things shape every decision below.

**P1. The September 16 deadline is soft.** Arc testnet is not being retired at mainnet
launch. It is receiving a hardfork on September 3. What closes on September 16 is the
attention window, not the environment. Plan for quality of output, not a sprint to a
date you invented.

**P2. The supply of evaluable services on Arc testnet is unproven and is the top
project risk.** Every competitor in §7 is on Base. The most likely reason is that the
addressable population on Arc is small. If Arc testnet has fewer than ten live, paid,
responsive services, the "20 services deeply" plan is dead on arrival. Test this
before building anything.

**P3. The riskiest assumption is not the schema, it is the judge.** The entire project
rests on an LLM evaluator producing verdicts that are consistent with itself across
reruns and consistent with a human on the same evidence. That is testable in an
afternoon with hand-written mock responses and zero blockchain. Test it first.

Everything is sequenced so that P2 and P3 get answered before any integration code
gets written.

---

## 1. Architecture

Seven components. The dependency structure matters more than the component list: the
measurement core (2, 5, 6) has no blockchain dependency at all and can be built and
validated standalone.

```
                        ┌──────────────────┐
                        │ 1. Purpose spec  │
                        │   (JSON schema)  │
                        └────────┬─────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
    ┌───────────────────┐  ┌──────────┐  ┌──────────────────┐
    │ 2. Phrasing       │  │ 3. Chain │  │ 6. Evaluator     │
    │    generator      │  │  binding │  │  (LLM judge)     │
    └─────────┬─────────┘  └────┬─────┘  └────────▲─────────┘
              │                 │                 │
              ▼                 │                 │
    ┌───────────────────┐       │      ┌──────────┴─────────┐
    │ 4. Shopper runner │───────┘      │ 5. Deterministic   │
    │  (buyer agents)   │              │    pre-checks      │
    └─────────┬─────────┘              └──────────▲─────────┘
              │                                   │
              ▼                                   │
    ┌───────────────────┐                         │
    │ Evidence store    │─────────────────────────┘
    │ (transcripts)     │
    └─────────┬─────────┘
              ▼
    ┌───────────────────┐
    │ 7. Publisher      │
    │  (static site)    │
    └───────────────────┘
```

### 1.1 Purpose spec

The contribution (O1). A versioned JSON document with two clearly separated blocks:

- **Hard constraints.** Machine-checkable. Max price, required output shape, latency
  ceiling, required fields, forbidden content. Evaluated deterministically. This
  mirrors AP2's Intent Mandate constraints and OmniAgentPay's spending guards, which
  is useful precedent to cite.
- **Soft purpose.** Not machine-checkable. What the buyer is trying to achieve, what
  would count as a good outcome, what would count as a bad one. Evaluated by the judge.

The split is the design. It keeps the deterministic part cheap and unarguable, and
confines LLM judgment to where it is actually needed. It also degrades gracefully: if
the judge is unavailable or contested, the hard constraint results still stand.

The document is hashed and bound before the request goes out. Nothing in it may
reference the response.

### 1.2 Phrasing generator

Produces N surface variations of one purpose. Must use more than one generator, or
every finding is an artifact of your prompt style (this is already in your §10). Plan:
two different models plus a hand-seeded set per purpose. Record which generator
produced which phrasing so you can check whether generator identity predicts outcome.
If it does, that is a finding, not a bug.

### 1.3 Chain binding

Writes the purpose hash on-chain before the outcome exists, and the verdict plus
evidence URI after. Two candidate paths, decide in Session 4:

- **ERC-8004 ReputationRegistry `giveFeedback`.** Fill `metadataURI`, `evidenceURI`,
  and `feedbackHash`, which Circle's own tutorial passes empty. Cheap, no new
  contract, and the narrative writes itself.
- **ERC-8183 job with `commitmentRef`.** Stronger binding if the field exists in the
  deployed contract. Unverified (O7). Fallback is the `description` field.

Not on the critical path for v1 correctness. Do not let it block the measurement work.

### 1.4 Shopper runner

Spawns buyer agents, holds a Circle developer-controlled wallet, executes the x402
payment flow or the 8183 job lifecycle, captures the full request and response,
records latency, cost, and tx hash. Boring integration code. Circle's quickstarts do
most of it.

### 1.5 Deterministic pre-checks

Evaluates the hard-constraint block. No LLM. Runs before the judge and its results are
passed to the judge as context, not as a verdict.

### 1.6 Evaluator

LLM judge. Receives the purpose, the rubric, and the response. Two protocol
requirements that are easy to skip and expensive to retrofit:

- **Blinding.** The judge does not see the service identity, the price, or which
  phrasing produced the response. Otherwise you get halo effects and your "does price
  predict quality" question (§11 item 4) becomes unanswerable from your own data.
- **Shuffling.** Responses from different services and phrasings are interleaved, not
  presented in service-grouped batches.

### 1.7 Publisher

Static site generated from the run data. See §4 for what it shows.

---

## 2. Phases

### Phase 0 — Prove the measurement works (no blockchain)

**Goal:** know whether an LLM judge can grade purpose satisfaction reliably enough to
build a project on.

Write 4 purposes and, by hand, 6 mock responses each spanning clearly good, clearly
bad, and genuinely ambiguous. Run the judge over all 24 three times.

**Exit criteria:**
- Self-consistency: same input, same verdict, at least 90% of the time on the clear
  cases.
- Human agreement: you grade the 24 blind, compare. Aim for 80%+ on clear cases.
- The ambiguous cases are where the interesting behavior lives. Do not average them
  away, catalog them.

If the judge cannot do this on hand-written cases, it will not do it on real ones, and
you need a different rubric or a different model before spending another hour.

**Cost:** a few dollars of API calls. **Blocking:** nothing.

### Phase 1 — Prove the supply exists

**Goal:** answer P2 with a number.

Enumerate every x402 service and ERC-8004 registered agent on Arc testnet. For each,
attempt one real paid request and record whether you got a usable response. The
empirical study (§6.1) found only 3% to 15% of registered agents on the big chains
have a live service endpoint. Expect worse on Arc.

**Gate decision.** Count of live, paid, responsive services:

| Count | Plan |
|---|---|
| 15+ | Original plan. Shop real services on Arc. |
| 5 to 14 | Reduced sweep on Arc plus self-deployed calibration services. |
| Under 5 | Pivot required. See below. |

**Pivot options, designed now rather than in a panic:**

- **A. Arc as record layer, Base as shopping floor.** Shop the large Base x402
  population, bind and publish verdicts on Arc. This is strictly more interesting than
  the original: it makes the cross-chain comparison (§11 item 11) a v1 feature instead
  of future work, and it sidesteps the reputation-silo problem by being explicit about
  it.
- **B. Deploy your own calibration services.** Six to eight x402 sellers with
  deliberately engineered quality profiles: one good, one flaky, one that only works
  with exact phrasing, one that returns the wrong shape, one that takes payment and
  returns nothing, one that degrades silently.

Option B is worth doing regardless of the count, because it gives you **known ground
truth**. That is the only way to demonstrate measurement integrity, which §6.2 flags
as the thing you actually care about and the thing the peer-prediction literature
warns is usually ignored. It also seeds your failure taxonomy (§11 item 2) with
designed failures before you go looking for real ones.

Strong recommendation: **B is v1 whatever the count is.** Real services are v1.1.

### Phase 2 — One end-to-end run

**Goal:** one purpose, one service, one payment, one verdict, one on-chain record, one
published page. Depth zero, width zero, but every link connected.

This is the demo. Everything after it is scaling.

### Phase 3 — The sweep

**Concrete first numbers for O3:**

```
6 services × 4 purposes × 5 phrasings × 3 repeats = 360 evaluations
```

At roughly $0.02 per judge call that is about $7 of inference and zero dollars of
testnet gas. Small enough to rerun the entire sweep when you change the rubric, which
you will, twice.

The repeats are not padding. They are how you separate service variance from judge
variance, and without them you cannot claim anything about either.

### Phase 4 — Publish

Site, methodology writeup, full data dump. Resolve O2 (naming services) before this
ships, not during.

---

## 3. Data model (O4)

```
Run
 └── Purpose (purpose_id, version, hash, hard_constraints{}, soft_purpose{}, rubric)
      └── Phrasing (phrasing_id, text, generator_id, seed_type)
           └── Attempt
                ├── attempt_id
                ├── service_id            (blinded at judge time)
                ├── request               (full)
                ├── response              (full, raw)
                ├── latency_ms
                ├── cost_usdc
                ├── tx_hash
                ├── timestamp
                ├── repeat_index
                ├── deterministic{}       (per hard constraint: pass / fail / n-a)
                └── verdict
                     ├── judge_model
                     ├── judge_run_index
                     ├── outcome          (served / partial / not-served / no-response)
                     ├── reasoning        (words, per D4)
                     └── evidence_uri
```

Verdict is a separate entity from attempt because you will judge the same attempt more
than once, and later with more than one model when you add the peer-prediction layer
(§11 item 1). Design for that now, it costs nothing today and is painful to retrofit.

Store attempts as append-only JSONL. Content-address the evidence. Publish the whole
thing (D12).

---

## 4. UI/UX

The product is not a dashboard. Eleven projects already ship dashboards and they all
show uptime.

**The one visual nobody else can produce** is the variance strip. Per service, per
purpose, a row of cells, one per attempt, colored by outcome. A service that works 90%
of the time regardless of phrasing looks like a solid bar. A service that works 90% of
the time only when phrased correctly looks like a broken comb. Those two are identical
on every existing leaderboard and completely different products. Make that difference
visible in one glance and the pitch makes itself.

Everything else follows from contestability (D12):

- **Drill-down is the product.** Click a cell, get the purpose, the phrasing, the raw
  response, the rubric, the judge's reasoning in words, and the tx hash. If a service
  operator disagrees with a verdict they should be able to see exactly what happened
  without asking you.
- **Show the judge's uncertainty.** Where three repeats disagreed, say so. Hiding it
  makes the whole thing look like fake determinism, which is what you criticized
  ERC-8004's numeric scores for.
- **Aggregate last, not first.** Lead with the distribution, offer the summary number
  underneath. The opposite ordering is what every competitor does and it is where the
  information gets destroyed.
- **Two audiences, two entry points.** Buyers want "which service should I use."
  Sellers want "why did I score badly and what phrasings break me." The second is D5
  and it is what stops you being purely an antagonist.

---

## 5. Session plan

Each session ends with something that runs or something decided. No session is pure
reading.

| # | Focus | Output | Unblocks |
|---|---|---|---|
| **2** | Supply census on Arc testnet. Cheap verifications in parallel: `commitmentRef` in deployed 8183 source (O7), arXiv:2606.26028 §8. | A number, and the gate decision from Phase 1. | Everything |
| **3** | Purpose schema v0.1 (O1). Hard and soft blocks. Write 4 real purposes against it. | `purpose.schema.json` plus 4 instances | S4, S5 |
| **4** | Evaluator rubric and blinding protocol (O8). Judge reliability test from Phase 0. | Rubric, reliability numbers, model choice | Go/no-go on the whole approach |
| **5** | Result record schema (O4). Scope lock (O3). Chain binding path decision. | Schemas locked, one decision recorded | S6, S8 |
| **6** | Build calibration services. Six x402 sellers with engineered quality profiles. | Deployed, documented ground truth | S7 |
| **7** | Build shopper runner. Wallet, payment flow, transcript capture. Run the quickstarts end to end here. | One paid request, captured | S8 |
| **8** | Wire evaluator plus deterministic pre-checks to the runner. Validate against calibration ground truth. | Phase 2 complete: one end-to-end run | S9 |
| **9** | Chain binding. Purpose hash before, verdict and evidence after. | On-chain record | S10 |
| **10** | Publisher. Variance strip plus drill-down. | Site rendering real data | S11 |
| **11** | Run the full sweep. | 360 evaluations of data | S12 |
| **12** | Analysis, failure taxonomy, writeup. Resolve O2. | Publication draft | — |

Sessions 3 through 5 are design and produce artifacts, not code. Do not skip them to
start building. The schema is the contribution and it is cheaper to argue with on
paper.

Sessions 2 and 4 are both gates. If either comes back badly, the plan changes and that
is the plan working.

---

## 6. Risks not yet in the context file

| Risk | Why it matters | Mitigation |
|---|---|---|
| **Service supply on Arc is too thin to shop** | Kills the stated v1 outright | Phase 1 census before any build. Pivots A and B designed in advance. |
| **Judge is not self-consistent** | Kills the project, not just the plan | Phase 0, before anything else. Cheap. |
| **Evaluator sees service identity or price** | Halo effects contaminate every finding, and makes the price-quality question unanswerable | Blinding and shuffling in the protocol from day one |
| **No ground truth to validate the evaluator against** | Measurement integrity is unprovable, which is the exact failure §6.2 warns about | Self-deployed calibration services with known quality profiles |
| **Solo scope creep** | 12 sessions becomes 40 | Every session ends in a runnable or a decision. Chain binding is explicitly not on the correctness critical path. |

---

## 7. Open items carried forward

Unchanged from the context file: O1, O2, O3, O4, O5, O6, O7, O8.

Newly scheduled: O1 in S3, O8 in S4, O3 and O4 and O7 in S5, O2 in S12.
O5 and O6 remain open and do not block the build.
