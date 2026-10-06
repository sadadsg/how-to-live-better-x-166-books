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
    "进化心理学": "进化心理学：心理的新科学",
    "AI未来已来": "AI未来已来：CEO、组织、个人的时代红利",
    "全球股市启示录": "全球股市启示录：行情脉络与板块轮动",
    "巴比伦": "巴比伦最富有的人",
    "巴菲特": "巴菲特致股东的信",
}
# 非拆书库书名的合法引用（法规名/官方报告/文献段里的外文与文章标题/被点名说明不在库内的书）
WHITELIST = {
    "献血法", "公募权益类基金投资者盈利洞察报告", "素问·上古天真论",
    "Flow", "Deep Work", "Attention Span", "Fault Lines", "过渡劳动",
    "黑客与画家",
    "城镇燃气管理条例", "高层民用建筑消防安全管理规定", "中国国民心理健康发展报告",
    "2025 年 A 股退市盘点", "How Many Stocks Make a Diversified Portfolio?",
    "Time Series Momentum", "十年前的 6124 点历史大顶", "错过涨幅最大的 10 天",
    "40 张图，坚定投资信心", "个人信息保护法", "商业特许经营管理条例",
    "市场主体登记管理条例", "老年人跌倒干预技术指南", "领事保护与协助条例",
    "禁止使用童工规定", "关于加快建设分级诊疗体系的若干措施",
    "人口死亡信息登记管理规范", "未成年人学校保护规定", "广告法",
    "网络产品安全漏洞管理规定",
}
# 佐证行强制文献段的豁免词（该行声明无对应命题/底表缺文献/与他条共用佐证）
EXEMPT = ("无对应命题", "未入底表", "无文献", "底表未附", "sources 与 url 均空", "缺文献")
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
        if not line.startswith("- 调研佐证"):
            continue
        # 硬规矩：佐证行必须附文献段，除非声明无对应命题/底表缺文献/与他条共用
        if ("｜文献：" not in line and not any(w in line for w in EXEMPT)
                and not re.search(r"无.{0,12}命题", line) and not re.search(r"同 \d+\.\d+", line)):
            bad.append(f"{f.name}: 佐证行缺文献段 → {line[:60]}…")
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
