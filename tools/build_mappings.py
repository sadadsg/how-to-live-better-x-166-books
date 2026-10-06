#!/usr/bin/env python3
"""guide/*.md（人工源）→ data/mappings.yaml + data/mappings.json + 内嵌数据的 index.html

mappings.yaml 定位为"衍生索引"：改动请改 guide 原文后重跑本脚本。
校验：各节记录数与 verify_guides.py 基线一致；书目/佐证主题对底表可核。
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "guide"
VF = ROOT / "data" / "vault-frameworks.yaml"
RV = ROOT / "data" / "research-verdicts.yaml"
OUT_YAML = ROOT / "data" / "mappings.yaml"
OUT_JSON = ROOT / "data" / "mappings.json"
TEMPLATE = ROOT / "tools" / "index_template.html"
OUT_HTML = ROOT / "index.html"

# verify_guides.py 2026-10-06 全量基线：节号 -> 记录数
BASELINE = {1: 11, 2: 16, 3: 22, 4: 16, 5: 30, 6: 12, 7: 8, 8: 17, 9: 7, 10: 15,
            11: 3, 12: 11, 13: 8, 14: 3, 15: 3, 16: 2, 17: 4, 18: 2, 19: 5,
            20: 2, 21: 2, 22: 7, 23: 12, 24: 2, 25: 1, 26: 1, 27: 2, 28: 2,
            29: 12, 30: 10, 31: 3, 32: 3, 33: 4, 34: 0}
TOTAL = sum(BASELINE.values())  # 258

BOOK_ALIASES = {
    "小懒财富自由之路": "小懒财富自由之路——从基金开始",
    "日本式衰退": "日本式衰退：不增长时代的全景避坑指南",
    "进化心理学": "进化心理学：心理的新科学",
    "AI未来已来": "AI未来已来：CEO、组织、个人的时代红利",
    "全球股市启示录": "全球股市启示录：行情脉络与板块轮动",
    "巴比伦": "巴比伦最富有的人",
    "巴菲特": "巴菲特致股东的信",
}

REC_HEAD = re.compile(r"^###\s*([✅🟡❌🔀])\s*(\d+)\.(\d+)\s*(.*)$")
H1 = re.compile(r"^#\s*(\d+)\s*(.+?)\s*×\s*拆书库对照")
GUIDE_LINE = re.compile(r"^- 指南条目：")
GRADE = re.compile(r"证据等级 ([ABC])")
BOOK = re.compile(r"《([^《》]+)》")
THEME = re.compile(r"(?:「([^「」]{4,24})」|《([^《》]{4,24})》)——")
URL = re.compile(r"\[出处\]\((https?[^)]+)\)")
GH_LINK = re.compile(r"\[原文\]\((https?[^)]+)\)")
ENTRY_TITLE = re.compile(r"「([^「」]+)」")

CANON_FIELDS = {"指南条目", "对应框架", "调研佐证"}


# 对应框架行里的非拆书库引用（内经章节名等）
IGNORE_BOOKS = {"素问·上古天真论"}


def norm_book(name: str) -> str:
    return BOOK_ALIASES.get(name, name)


def parse_guide(path: Path, themes_ok):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sec_no, sec_name = None, None
    for line in lines:
        m = H1.match(line)
        if m:
            sec_no, sec_name = int(m.group(1)), m.group(2).strip()
            break
    if sec_no is None:
        raise SystemExit(f"{path.name}: 找不到 H1")

    def books_from(line_text):
        out = []
        for b in BOOK.findall(line_text):
            nb = norm_book(b)
            if nb not in themes_ok and nb not in IGNORE_BOOKS:
                out.append(nb)
        return out

    records = []
    cur = None
    for line in lines:
        m = REC_HEAD.match(line)
        if m:
            if cur:
                records.append(cur)
            cur = {
                "section": sec_no,
                "section_name": sec_name,
                "verdict": m.group(1),
                "entry": f"{sec_no}.{m.group(3)}",
                "record_title": m.group(4).strip(),
                "entry_grade": None,
                "entry_title": None,
                "github": None,
                "books": [],
                "corroboration": None,
                "themes": [],
                "papers": [],
                "paper_urls": [],
                "has_literature": False,
                "points": [],
            }
            continue
        if cur is None:
            continue
        if line.startswith("- 指南条目："):
            g = GRADE.search(line)
            cur["entry_grade"] = g.group(1) if g else None
            t = ENTRY_TITLE.search(line)
            cur["entry_title"] = t.group(1) if t else None
            u = GH_LINK.search(line)
            cur["github"] = u.group(1) if u else None
            continue
        if line.startswith("- 对应框架："):
            cur["books"] = books_from(line)
            continue
        if line.startswith("- 调研佐证："):
            cur["corroboration"] = line[2:].strip()
            cur["has_literature"] = "｜文献：" in line
            for a, b in THEME.findall(line):
                name = (a or b).strip()
                if len(name) <= 24 and not re.search(r"[，。；：]", name):
                    cur["themes"].append(name)
            cur["papers"] = [s for s in re.findall(r"｜文献：(.+)$", line)]
            cur["paper_urls"] = URL.findall(line)
            continue
        if line.startswith("- "):
            label = line[2:].split("：", 1)[0]
            if label not in CANON_FIELDS:
                cur["points"].append(line[2:].strip())
            continue
        if line.startswith(("#", ">")) or not line.strip():
            continue
        # 记录块内的续行并入最后一条 point
        if cur["points"]:
            cur["points"][-1] += " " + line.strip()
    if cur:
        records.append(cur)
    # 无对应框架行的记录回退用标题里的书名
    for r in records:
        if not r["books"]:
            head_books = r["record_title"].split("↔", 1)
            if len(head_books) == 2:
                r["books"] = books_from(head_books[1])
    return sec_no, sec_name, records


def main():
    books_ok = {b["book"] for b in yaml.safe_load(VF.read_text())["books"]}
    themes_ok = {r["theme"] for r in yaml.safe_load(RV.read_text())["reports"]}

    all_records, problems = [], []
    counts = {}
    for path in sorted(GUIDE.glob("*.md")):
        sec_no, sec_name, recs = parse_guide(path, themes_ok)
        counts[sec_no] = len(recs)
        all_records.extend(recs)
        if len(recs) != BASELINE.get(sec_no):
            problems.append(f"{path.name}: 记录数 {len(recs)} != 基线 {BASELINE.get(sec_no)}")
        for r in recs:
            for b in r["books"]:
                if b not in books_ok:
                    problems.append(f"{path.name} {r['entry']}: 书名不可核 → {b}")
            for t in r["themes"]:
                if t not in themes_ok:
                    problems.append(f"{path.name} {r['entry']}: 佐证主题不可核 → {t}")
            if r["entry_grade"] is None:
                problems.append(f"{path.name} {r['entry']}: 缺证据等级")
            if r["github"] is None:
                problems.append(f"{path.name} {r['entry']}: 缺 GitHub 原文链接")

    from collections import Counter
    vc = Counter(r["verdict"] for r in all_records)
    print(f"records={len(all_records)} verdicts={dict(vc)}")
    print(f"佐证行={sum(1 for r in all_records if r['corroboration'])} "
          f"带文献段={sum(1 for r in all_records if r['has_literature'])} "
          f"带论文URL={sum(1 for r in all_records if r['paper_urls'])}")
    if len(all_records) != TOTAL:
        problems.append(f"总数 {len(all_records)} != {TOTAL}")
    if (vc.get("✅", 0), vc.get("🟡", 0), vc.get("❌", 0), vc.get("🔀", 0)) != (123, 54, 2, 79):
        problems.append(f"四档分布 {dict(vc)} != 基线 (123,54,2,79)")
    if problems:
        print(f"FAIL ({len(problems)}):")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    all_records.sort(key=lambda r: (r["section"], int(r["entry"].split(".")[1])))
    sections = [{"no": n, "name": nm, "records": sum(1 for r in all_records if r["section"] == n)}
                for n, nm in sorted({(r["section"], r["section_name"]) for r in all_records})]
    # 34 节也要在（即使 0 记录）
    have = {s["no"] for s in sections}
    for n, cnt in BASELINE.items():
        if n not in have:
            nm = next((r["section_name"] for r in all_records if r["section"] == n), None)
            if nm is None:
                # 从文件名取
                f = next(GUIDE.glob(f"{n:02d}-*.md"))
                nm = f.stem.split("-", 1)[1]
            sections.append({"no": n, "name": nm, "records": 0})
    sections.sort(key=lambda s: s["no"])

    payload = {"generated_by": "tools/build_mappings.py",
               "stats": {"records": len(all_records), "verdicts": dict(vc)},
               "sections": sections, "records": all_records}

    with OUT_YAML.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False, width=200)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    tpl = TEMPLATE.read_text(encoding="utf-8")
    data_js = json.dumps(payload, ensure_ascii=False)
    html = tpl.replace("/*__MAPPINGS__*/null", data_js)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"OK: {OUT_YAML.name} {OUT_YAML.stat().st_size//1024}KB / "
          f"{OUT_JSON.name} {OUT_JSON.stat().st_size//1024}KB / "
          f"index.html {OUT_HTML.stat().st_size//1024}KB")


if __name__ == "__main__":
    main()
