#!/usr/bin/env python3
"""Validate, score and seal every purpose in spec/examples/."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from purposelib import validate, specificity, seal, verify_seal

EX = Path(__file__).resolve().parents[2] / "spec" / "examples"

rows = []
for p in sorted(EX.glob("*.json")):
    doc = json.loads(p.read_text())
    v = validate(doc)
    spec = specificity(doc)
    sealed = seal(doc, sealed_at=doc["issuedAt"])
    ok, h = verify_seal(sealed)
    p.write_text(json.dumps(sealed, indent=2) + "\n")
    rows.append((p.name, v, spec, ok, h))

print(f"{'file':38} {'valid':6} {'spec':6} {'hash'}")
print("-" * 92)
for name, v, spec, ok, h in rows:
    print(f"{name:38} {str(v.ok):6} {spec.score:<6} {h[:20]}...")

print("\n=== detail ===")
for name, v, spec, ok, h in rows:
    print(f"\n{name}")
    print(f"  specificity {spec.score}   {spec.detail}")
    print(f"  components  {spec.components}")
    for e in v.errors:
        print(f"  ERROR   {e}")
    for w in v.warnings:
        print(f"  WARN    {w}")
