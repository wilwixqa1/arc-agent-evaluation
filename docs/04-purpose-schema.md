# Purpose Document Schema v0.1.0 — Design Notes

**Resolves:** O1
**Artifacts:** `spec/purpose.schema.json`, `spec/examples/`, `tools/purpose/`
**Status:** v0.1.0. Four sealed examples, 23 passing property tests.

---

## 1. What this has to do

A purpose document states what a buying agent is trying to achieve, is sealed before
the outcome is knowable, and is later used to grade whether the outcome served it.

That gives four requirements, and they pull against each other:

1. **Comparable across agents.** Otherwise there is no dataset, just anecdotes.
2. **Not collapsible to a number.** The whole critique of ERC-8004's reputation field
   is that `95` carries no information (§7.1, C1). Reproducing that failure with extra
   steps would be worse than useless.
3. **Sealed before the outcome.** Otherwise it is a rationalization, not a commitment.
4. **Resistant to self-serving vagueness.** An agent graded on its own stated purpose
   will state an easy one (O6).

Requirement 4 is the hard one and most of the design below exists to serve it.

---

## 2. The hard/soft split

The document has two evaluation blocks.

**`constraints` is machine-checkable.** Price ceiling, latency ceiling, response
format, required fields, required and forbidden substrings, numeric bounds, freshness.
No LLM touches these. A violation is a fact, not an opinion, and is not contestable.

**`objective` is LLM-graded.** Goal, success criteria, disqualifiers, out-of-scope.

Three reasons for the split:

- It confines LLM judgment to where it is actually needed, which keeps cost down and
  keeps the contestable surface small.
- It degrades gracefully. If the judge is unavailable, disputed, or later shown to be
  unreliable, the constraint results still stand on their own.
- It has precedent on both sides. AP2's Intent Mandate separates hard constraints (max
  price, expiry, allowed merchants) from the natural-language request. OmniAgentPay,
  the January hackathon winner, enforces exactly this class of constraint at the wallet
  layer. We are not inventing a distinction, we are extending one that already exists
  into the part nobody grades.

---

## 3. Disqualifiers are the load-bearing field

`objective.disqualifiers` is required, minimum one, and it is the single most important
design decision in the schema.

Anyone can write a success criterion that is trivially satisfied. "The response is
helpful" passes almost always. But writing a *disqualifier* means naming a specific way
the thing could fail, and vacuous disqualifiers are conspicuously hard to write. Compare:

> **Weak success criterion:** "The information provided is of reasonably high quality."
>
> **Real disqualifier:** "The figure returned is USDC supply on Ethereum, Base, or any
> chain other than chainId 5042002."

The second names a concrete failure mode the author must have anticipated. You cannot
produce it without actually thinking about what going wrong looks like. Requiring it
forces engagement that a success-criteria-only schema does not.

Weighting reflects this: disqualifiers carry 0.25 of the specificity score, the largest
single component.

Two supporting rules:

- **Minimum two success criteria.** One criterion is a vibe check wearing a list.
- **`necessary: true`** marks a criterion whose failure caps the verdict at
  `partially_served` regardless of the others, so an important criterion cannot be
  outvoted by a pile of easy ones.

---

## 4. Specificity, and why it is computed rather than judged

`tools/purpose` computes a specificity score from the document alone, before any
response exists. Six components:

| Component | Weight | What it measures |
|---|---|---|
| `disqualifiers` | 0.25 | Count, saturating at 3 |
| `concrete_referents` | 0.20 | Share of statements containing a number, address, date, quoted literal, or identifier |
| `criteria_count` | 0.15 | Count, saturating at 5 |
| `unhedged` | 0.15 | Share of statements *without* an unqualified hedge word |
| `machine_checkable` | 0.15 | How many kinds of deterministic constraint are set |
| `task_inputs` | 0.10 | Count of concrete referents in the task itself |

Three properties matter more than the weights:

**It is outcome-independent.** Computed from the document only. It cannot be influenced
by what came back, which is what makes it usable as a drift metric.

**It is transparent.** Every component is a count a reader can verify by hand. No model
in the loop, no black box. When someone disputes a score they can recount.

**It is not a quality score.** A low-specificity purpose is not a bad question, it is an
ungradeable one. The metric says how much the verdict on this purpose can be trusted,
not whether the buyer wanted something worthwhile.

Measured separation on the four examples:

| Example | Specificity | Schema-valid |
|---|---|---|
| `p01-usdc-supply-lookup` | 0.913 | yes |
| `p02-x402-settlement-summary` | 0.900 | yes |
| `p03-proxy-upgrade-analysis` | 0.814 | yes |
| `p04-WEAK-negative-fixture` | **0.143** | **yes** |

`p04` is deliberately gamed: two hedge-word criteria, one vacuous disqualifier, no
constraints, no task inputs, blinding switched off. **It passes structural validation.**
That is intentional and worth stating plainly: the schema cannot stop vagueness, so it
measures it instead. Rejecting `p04` outright would push gaming into forms the schema
cannot see. Scoring it at 0.143 and publishing that number alongside every verdict
derived from it is the honest alternative.

The validator does emit warnings on `p04` (three hedged statements, empty constraints,
blinding disabled), so the failure is visible without being fatal.

### The drift metric

O6 asked how to stop agents writing easier purposes over time. Answer: you cannot stop
it, but this makes it visible. Track mean specificity per issuer over time. If it
declines, agents are learning to game the grader. That trend is arguably a more
interesting result than any individual verdict, and no other system in this space can
produce it because no other system asks for a commitment first.

---

## 5. Sealing

Canonicalize with **RFC 8785 (JSON Canonicalization Scheme)**, hash with **SHA-256**.

RFC 8785 rather than an ad-hoc serialization because the IETF agent audit trail draft
(`draft-sharif-agent-audit-trail-00`, §7.3 of the context doc) uses the same
canonicalization with SHA-256 hash chaining. A sealed purpose drops into that ecosystem
without translation. Given that the whole thesis is joining the declare-before layer to
the record-after layer, sharing their canonicalization is close to free and worth
having.

The hash is computed over the document with the entire `binding` block removed, not
with one field blanked. That means a purpose sealed off-chain and the same purpose
later written to a job have identical hashes: settlement metadata attaches afterward
without disturbing the seal. Tested.

### On-chain binding

`commitmentRef` does not exist in the Arc ERC-8183 deployment (O7, resolved negative).
It is not needed:

| Slot | Type | Written by | When | Carries |
|---|---|---|---|---|
| `description` | string | client | `createJob` | purpose hash |
| `deliverable` | bytes32 | provider | `submit` | response hash |
| `reason` | bytes32 | evaluator | `complete` / `reject` | verdict hash |

`description` is set at job creation and never mutated, which is a genuine
pre-commitment slot. SHA-256 output is 32 bytes, so it fits `bytes32` directly for the
other two. The full loop binds using only what is already deployed, with no new
contract and no admin whitelist.

For x402, where there is no job object, the same hash goes in a session record
referenced by `feedbackURI` on an ERC-8004 `giveFeedback` call. Those fields exist and
Circle's tutorial passes them empty.

---

## 6. Blinding is in the schema, not the harness

`evaluation.blinding` declares what the judge must not see: provider identity, price,
and which phrasing produced the response.

It lives in the purpose rather than in the runner's configuration for one reason: it is
part of the sealed commitment. Deciding after the fact that the judge could see the
price is exactly the sort of quiet methodology change that makes results unfalsifiable.
Sealing it means the blinding condition is part of the record, and disabling it is
visible to anyone reading the document.

Practical consequence: with price hidden, "does paying more get you better outcomes"
(future work item 5) stays answerable from our own data. With price visible it never
would be, and the contamination would be undetectable after the fact.

---

## 7. What is deliberately absent

**Phrasing variations.** The purpose is the invariant; phrasings are the treatments.
Putting them in the same document would confuse the thing being committed to with the
thing being varied. `task.summary` is the seed the generator varies, and it is
explicitly not the thing being graded.

**Numeric quality scores.** No overall 0-100 rating anywhere. Verdicts are enum plus
per-criterion outcomes plus reasoning in words (D4). A number can always be derived
downstream; the reverse is not true.

**Evaluator identity and model.** Belongs on the verdict record, not the purpose. One
purpose will be judged by several models once the peer prediction layer exists.

**Anything an LLM must interpret to enforce.** The hedge-word check is a warning, not a
rejection, because "is this criterion falsifiable" is itself a judgment call and would
smuggle a model into the validation path.

---

## 8. Known weaknesses

**The hedge word list is English-only and finite.** It catches obvious vagueness and
will miss sophisticated vagueness. It is a smoke detector, not a proof.

**Concrete-referent detection is a regex.** A criterion can cite a number and still be
unfalsifiable. The metric will overrate it. Accepted: the alternative is an LLM in the
scoring path, which destroys reproducibility.

**Weights are asserted, not derived.** There is no ground truth on what specificity
"should" weigh. Once we have verdicts across many purposes we can check whether
specificity actually predicts inter-judge agreement, and refit. Until then the honest
description is: a transparent index, not a validated instrument.

**Two minimum criteria may be too lenient.** Watch whether real purposes cluster at the
minimum. If they do, raise it.

**Not yet tested against a judge.** Everything above is structural. Whether these
criteria actually produce consistent verdicts is the Phase 0 question, and it is next.

---

## 9. Next

- Phase 0 judge reliability: 4 purposes × 6 hand-written mock responses × 3 runs, no
  blockchain. Does the judge agree with itself, and with a human, on these criteria?
- The verdict record schema, which references `purposeHash` and per-criterion ids.
- The evaluator rubric and prompt (O8).
- Once verdicts exist: check whether specificity predicts inter-judge agreement, and
  refit the weights against that rather than against intuition.
