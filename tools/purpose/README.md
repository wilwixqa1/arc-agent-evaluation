# purpose

Tooling for purpose documents: the sealed, pre-commitment statement of what a buying
agent is trying to achieve, which the outcome is later graded against.

Design rationale in [`docs/04-purpose-schema.md`](../../docs/04-purpose-schema.md).
Schema in [`spec/purpose.schema.json`](../../spec/purpose.schema.json).

## Install

```bash
pip install -r requirements.txt
```

## Use

```python
from purposelib import validate, specificity, seal, verify_seal

doc = json.loads(Path("spec/examples/p01-usdc-supply-lookup.json").read_text())

v = validate(doc)          # schema + semantic rules; .ok, .errors, .warnings
s = specificity(doc)       # 0..1, outcome-independent; .score, .components, .detail
sealed = seal(doc)         # fills binding.purposeHash
ok, h = verify_seal(sealed)
```

```bash
python seal_examples.py    # validate, score and re-seal every example
python tests/test_purpose.py
```

## What the pieces do

**`canonicalize`** serializes per RFC 8785 (JSON Canonicalization Scheme). Same
canonicalization the IETF agent audit trail draft uses, so a sealed purpose is
ingestible by that ecosystem without translation.

**`purpose_hash`** is SHA-256 over the canonical bytes with the entire `binding` block
removed. A purpose sealed off-chain and the same purpose later written to a job produce
identical hashes, so settlement metadata attaches without disturbing the seal.

**`validate`** runs JSON Schema plus rules the schema cannot express: duplicate
criterion ids, criteria that merely restate `task.summary`, hedge words with no
concrete referent, empty constraint blocks, disabled blinding.

**`specificity`** scores how falsifiable a purpose is, from the document alone, before
any response exists. Transparent by construction: every component is a count you can
verify by hand. Low specificity does not mean a bad question, it means an ungradeable
one.

## On-chain binding

`commitmentRef` does not exist in the Arc ERC-8183 deployment. It is not needed:

| Slot | Type | Written by | When | Carries |
|---|---|---|---|---|
| `description` | string | client | `createJob` | purpose hash |
| `deliverable` | bytes32 | provider | `submit` | response hash |
| `reason` | bytes32 | evaluator | `complete` / `reject` | verdict hash |

`description` is set at creation and never mutated, which makes it a genuine
pre-commitment slot. No new contract and no admin whitelist required.
