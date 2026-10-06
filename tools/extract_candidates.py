#!/usr/bin/env python3
"""按关键词从两份底表抽候选：tools/extract_candidates.py --keys "a,b,c" --out data/candidates/XX.md

用法（每节一次）：
  python3 tools/extract_candidates.py --keys "睡眠,咖啡因" --num 03
输出 Markdown：前半是拆书库命中书目（含命中框架），后半是调研报告命中命题。
"""
import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VF = ROOT / "data" / "vault-frameworks.yaml"
RV = ROOT / "data" / "research-verdicts.yaml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", required=True, help="逗号分隔关键词")
    ap.add_argument("--num", required=True, help="节号，如 03")
    args = ap.parse_args()
    keys = [k.strip().lower() for k in args.keys.split(",") if k.strip()]
    if not keys:
        raise SystemExit("no keys")
    hit = lambda s: any(k in (s or "").lower() for k in keys)  # noqa: E731

    vf = yaml.safe_load(VF.read_text(encoding="utf-8"))["books"]
    rv = yaml.safe_load(RV.read_text(encoding="utf-8"))["reports"]

    out = [f"# 候选集 0{args.num[-1]}（keys: {', '.join(keys)}）\n"]
    n_books = 0
    for b in vf:
        fw_hits = [fw for fw in b.get("frameworks", []) if hit(fw["name"]) or hit(fw.get("core", ""))]
        ci_hits = [c for c in b.get("counterintuitive", []) if hit(c.get("title", "")) or hit(c.get("claim", ""))]
        if not fw_hits and not ci_hits:
            continue
        n_books += 1
        out.append(f"\n## 书目《{b['book']}》 — {b.get('author','')}（{b['category']}）")
        if b.get("takeaway"):
            out.append(f"- 一句话：{b['takeaway']}")
        for fw in fw_hits:
            out.append(f"- 框架「{fw['name']}」：{fw.get('core','')}")
        for c in ci_hits:
            out.append(f"- 反常识「{c.get('title','')}」：{c.get('claim','')}")
    out.append(f"\n---\n命中书目：{n_books}")

    n_reports = 0
    for r in rv:
        cl = [c for c in r.get("claims", []) if hit(c.get("claim", "")) or hit(c.get("evidence", ""))]
        if not cl:
            continue
        n_reports += 1
        out.append(f"\n## 调研报告「{r['theme']}」（{r.get('category','')}）")
        for c in cl:
            out.append(f"- [{c['verdict']}] {c['claim']}｜原判定:{c.get('original','')}｜证据:{c.get('evidence','')[:90]}｜url:{c.get('url','')}")
    out.append(f"\n命中调研报告：{n_reports}")

    dest = ROOT / "data" / "candidates" / f"{args.num}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"{dest} books={n_books} reports={n_reports} lines={len(out)}")


if __name__ == "__main__":
    main()
