#!/usr/bin/env python3
"""合并 data/fragments/*.yaml → data/research-verdicts.yaml，并做 schema 校验。"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FRAG = ROOT / "data" / "fragments"
OUT = ROOT / "data" / "research-verdicts.yaml"
VALID = {"支持", "部分支持", "存疑", "证伪"}
REQ = {"claim", "verdict", "original", "evidence", "sources", "url"}

records, errors = [], []
for p in sorted(FRAG.glob("*.yaml")):
    try:
        docs = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        errors.append(f"{p.name}: YAML 解析失败 {e}")
        continue
    if isinstance(docs, dict):
        docs = [docs]
    for rec in docs or []:
        if not isinstance(rec, dict) or "theme" not in rec:
            errors.append(f"{p.name}: 缺 theme 字段")
            continue
        for c in rec.get("claims", []):
            missing = REQ - set(c)
            if missing:
                errors.append(f"{p.name}/{rec['theme']}: 缺字段 {missing}")
            if c.get("verdict") not in VALID:
                errors.append(f"{p.name}/{rec['theme']}: verdict 非法 {c.get('verdict')!r}")
        records.append(rec)

records.sort(key=lambda r: (r.get("category", ""), r.get("theme", "")))
with OUT.open("w", encoding="utf-8") as f:
    yaml.safe_dump(
        {"generated": "merge_research_verdicts.py", "count": len(records),
         "reports": records},
        f, allow_unicode=True, sort_keys=False, width=200,
    )

n_claims = sum(len(r.get("claims", [])) for r in records)
from collections import Counter
vc = Counter(c.get("verdict") for r in records for c in r.get("claims", []))
url_ok = sum(1 for r in records for c in r.get("claims", []) if c.get("url"))
print(f"reports={len(records)} claims={n_claims} verdicts={dict(vc)} url覆盖={url_ok}/{n_claims}")
if errors:
    print(f"ERRORS ({len(errors)}):")
    for e in errors[:30]:
        print(" -", e)
    sys.exit(1)
print("schema OK")
