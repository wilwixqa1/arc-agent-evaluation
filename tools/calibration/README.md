# calibration

Six x402 sellers with deliberately engineered quality profiles, so the evaluator can
be tested against ground truth we already know.

## Why these exist

Consistency is not correctness. A judge can be perfectly self-consistent and
consistently wrong, and the only way to tell is to grade responses whose quality is
known in advance. That is measurement integrity, which arXiv:2108.05521 identifies as
the thing peer-prediction work usually optimizes away and the thing this project
actually cares about.

They also seed the failure taxonomy with designed failures before we look for real
ones, and on Arc they are the only shoppable services in existence: 0 of 250 sampled
agents had a reachable endpoint.

## The profiles

| id | Behaviour | What it tests |
|---|---|---|
| `honest` | Correct, complete, provenance included | Control. Anything failing here is our bug. |
| `flaky` | Correct ~70% of attempts, errors otherwise, independent of phrasing | Variance that is not phrasing-driven |
| `brittle` | Correct only when the query matches an expected pattern | **The case for D3** |
| `deadbeat` | Takes payment, returns HTTP 200 with an empty body | Paid and got nothing |
| `truncator` | Well-formed but silently stripped of provenance | Silent quality degradation |
| `confabulator` | Always confident and well-formed, content fabricated ~50% | Correct shape vs correct content |

## Measured separation

108 attempts: 6 profiles × 6 phrasings × 3 repeats, against the `p01` purpose, using
**only the deterministic constraint checker with no judge involved**.

| profile | passes | constraint violated | no response |
|---|---|---|---|
| honest | 18 | 0 | 0 |
| flaky | 13 | 0 | 5 |
| brittle | 3 | 15 | 0 |
| deadbeat | 0 | 0 | 18 |
| truncator | 0 | 18 | 0 |
| confabulator | **18** | 0 | 0 |

Three things worth reading off that table.

**An uptime monitor sees 103 of 108 attempts return HTTP 200.** That is 95.4% uptime
across a service population where exactly one of six is actually good. `deadbeat` takes
payment and returns nothing, and it is 100% "up". Every tool in the competitive
landscape would rank these six as near-identical.

**`brittle` fails on five phrasings out of six.** Canonical passes 3 of 3; every
paraphrase fails 3 of 3. It never errors and never times out, so it is invisible to
liveness monitoring by construction. This is the case for the phrasing swarm, and it is
now demonstrated rather than argued.

**`confabulator` passes every hard constraint, and half its answers are fabricated.**
Constraints check shape and cannot see content. That is exactly the gap the LLM judge
exists to fill, and it is the profile that will show whether the judge is grading
substance or form.

## Run

```bash
python services.py --port 8402          # serve
python services.py --manifest           # ground truth, machine readable
python client.py --resource usdc-supply --repeats 3
python tests/test_calibration.py        # 30 tests, no network beyond localhost
```

Resources: `usdc-supply`, `x402-summary`, `contract-analysis`, matching the first three
example purposes.

## Determinism

Behaviour is seeded on `(profile, attemptId)`. The same attempt always produces the
same response, so a rerun reproduces the dataset exactly and variance across repeats
comes from the seed changing rather than wall-clock randomness. Without that you cannot
separate service variance from judge variance, which is the entire reason for repeats.

## Ground truth never reaches the judge

Each response carries an `X-Calibration-Note` header describing what the service just
did. The client lifts it into `attempt.groundTruth` and `Attempt.for_judge()` strips
both that and the profile identity. Ground truth is for scoring the evaluator, never
for informing it.

## Phrasings

`phrasings.py` holds hand-written variations: canonical, three paraphrases, a terse
form and a verbose form, per resource. Model-generated variations come later and need
an API key, but hand-seeded ones are required regardless. If one generator writes every
variation, "optimal phrasing" collapses into "phrasing our generator produces" and
every finding becomes an artifact of prompt style. `generator` is recorded per phrasing
so we can test whether generator identity predicts outcome; if it does, that is a
finding rather than a bug.

## What is mocked

Settlement. The 402 envelope, the payment header, and the retry are real, so the same
client works against a live service unchanged, but nothing is submitted on chain. The
`X-PAYMENT` payload carries a placeholder signature where the buyer's EIP-3009
authorization goes on a real run.
