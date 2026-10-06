#!/usr/bin/env python3
"""核验 guide/*.md 引用真实性：书名必须存在于 vault-frameworks.yaml，
调研佐证主题名必须存在于 research-verdicts.yaml。"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
books = {b["book"] for b in yaml.safe_load((ROOT / "data/vault-frameworks.yaml").read_text())["books"]}
themes = {r["theme"] for r in yaml.safe_load((ROOT / "data/research-verdicts.yaml").read_text())["reports"]}

# 底表里的别名（guide 短名/通称 → frontmatter 全称，人工维护）
BOOK_ALIASES = {
    "小懒财富自由之路": "小懒财富自由之路——从基金开始",
    "日本式衰退": "日本式衰退：不增长时代的全景避坑指南",
}
# 非拆书库书名的合法引用（法律名等）
WHITELIST = {"献血法", "公募权益类基金投资者盈利洞察报告"}
# 佐证行里的主题名提取：出现在「《X》」或「《X》——」或「：X」引号中；本仓格式用「…《主题》…」与「：主题」两种
# guide 文档里调研佐证统一写法是 「主题名」——…（带引号）
bad = []
for f in sorted((ROOT / "guide").glob("*.md")):
    text = f.read_text(encoding="utf-8")
    for name in set(re.findall(r"《([^《》]+)》", text)):
        n = BOOK_ALIASES.get(name, name)
        if n not in books and name not in themes and name not in WHITELIST:
            bad.append(f"{f.name}: 书名不存在于底表 → {name}")
    for line in text.splitlines():
        if "调研佐证" not in line:
            continue
        for name in set(re.findall(r"「([^「」]{4,24})」——", line)) | set(re.findall(r"《([^《》]{4,24})》——", line)):
            if name not in themes:
                bad.append(f"{f.name}: 佐证主题名不存在于底表 → {name}")
if bad:
    print(f"FAIL ({len(bad)}):")
    for b in bad:
        print(" -", b)
else:
    print("OK: 全部书名与佐证主题名可在底表中核对")

# 统计四档
from collections import Counter
total = Counter()
for f in sorted((ROOT / "guide").glob("*.md")):
    c = Counter(re.findall(r"^### (✅|🟡|❌|🔀)", f.read_text(encoding="utf-8"), re.M))
    print(f.name, dict(c), "total", sum(c.values()))
    total += c
print("ALL:", dict(total), "sum", sum(total.values()))
