# judge

Rubric-driven evaluation of responses against sealed purposes.

Rubric: [`spec/rubric/v0.1.0.md`](../../spec/rubric/v0.1.0.md)

## The one design choice that matters

**The judge never gives an overall verdict.** It answers one narrow yes-or-no question
per success criterion and per disqualifier. The verdict is then computed from those
answers by a deterministic rule in `judgelib/verdict.py`.

"Did the response state a block number above 59000000" is a question a model answers
the same way on repeated runs. "Was this response good" is not. Narrowing the question
is the largest available lever on judge consistency, and it makes a disputed verdict
point at a specific criterion instead of a vibe.

The derivation rule is deliberately absent from the prompt. A judge that knew how
answers combine could reason backward toward a preferred outcome.

## Phase 0

```bash
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY / GOOGLE_API_KEY
export JUDGE_PROVIDER=anthropic
python run_phase0.py --repeats 3

python run_phase0.py --dry-run      # assemble all 24 prompts, call nothing
python tests/test_judge.py          # 44 tests, no key needed
```

24 hand-labelled fixtures across the four example purposes: 13 clear (3 served, 10 not
served) and 11 ambiguous. A full run is 72 calls.

Exit criteria, measured on clear fixtures only:

| Bar | Threshold |
|---|---|
| Self-consistency across 3 repeats | ≥ 90% |
| Agreement with the human label | ≥ 80% |
| Criterion-level consistency | reported, no threshold |

**Ambiguous fixtures are excluded from both bars and are not failures.** They
characterize behaviour at the boundary. A judge that is confidently decisive on a
genuinely ambiguous case is worse than one that wavers, so their disagreement rate is
reported separately as a property of the fixture set.

If the bars are missed, fix the rubric or change the model. Do not lower the bar.

## Fixtures worth knowing about

- **`p04-f2`** is the key one. Vacuous filler prose judged against the deliberately
  vacuous `p04` purpose (specificity 0.143). Low consistency here is a finding about
  the purpose, not the judge, and it is the empirical case that low-specificity
  purposes are ungradeable.
- **`p04-f3`** is confidently wrong but well formed. Tests whether "helpful and
  relevant" criteria catch factual falsehood at all.
- **`p01-f6`** discloses that its value is cached. Whether that trips "does not
  silently substitute" turns on how load-bearing the judge reads "silently".
- **`p03-f5`** says "an admin role" without naming it, sitting exactly on the line
  where a criterion demands the specific mechanism rather than a generic description.

## Providers

One interface, three backends, chosen by `JUDGE_PROVIDER`. Adding one is a single
class in `judgelib/providers.py`. Multi-provider matters twice: it separates judge
variance from service variance now, and it is the substrate for the peer prediction
layer later. Nothing here needs a key to import or test; only `.complete()` calls out.

## Blinding

`blind_attempt` strips provider, price and phrasing fields, walking nested structures,
and reports what it removed. `scrub_text` catches provider names that leak inside the
response body, where field-level blinding does nothing. Fixtures are shuffled before
judging, because blinding without shuffling leaks the grouping through ordering.

Blinding is declared in the sealed purpose, not in this runner's configuration, so
turning it off is part of the permanent record.
