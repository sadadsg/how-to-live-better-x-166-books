#!/usr/bin/env python3
"""解析拆书笔记（166 篇）→ data/vault-frameworks.yaml

按探索结论处理已知坑：
- 两代模板编号（新式 "1. 标题" / 旧式 "一、标题"）→ 标题去编号后按文字匹配
- 框架 H3 四种风格（框架N：/框架一：/2.1/第一层·第X章）→ 不按字面匹配，
  直接取「思维框架」H2 与下一个 H2 之间的所有 H3
- 31 篇的 `## 目录` 节整段跳过
- fenced code block 先切分，防 ASCII 框图里的 |、--- 干扰
- 反常识 H3 用带圈数字 ❶-❿ 编号，条目内取「大众认知/作者」两行
- 《亲密关系》frontmatter 缺书名/作者 → 文件名《X》兜底
- 相关链接节名有变体（相关链接/关联笔记/附：...），且可能有多个
"""
import re
import sys
from pathlib import Path

import yaml

VAULT = Path("/Users/bwsuaideyipi/Documents/Obsidian Vault/hanako-intro/拆书笔记")
OUT = Path(__file__).resolve().parent.parent / "data" / "vault-frameworks.yaml"

H2 = re.compile(r"^## (.+?)\s*$")
H3 = re.compile(r"^### (.+?)\s*$")
FENCE = re.compile(r"^(```|~~~)")
# 标题去编号：1. / 一、 / 第X章 / 第一部分 / 框架一： / 框架1： / 2.1 / ❶
NUM_PREFIX = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*[\.、．]?\s*|[一二三四五六七八九十]+[、\.．]\s*"
    r"|第[一二三四五六七八九十百\d]+[章节讲部分层]\s*|第?[一二三四五六七八九十]+部分\s*"
    r"|框架[一二三四五六七八九十\d]+[：:.、]\s*|[❶❷❸❹❺❻❼❽❾❿]\s*|附录[一二三四五六七八九十\d]*[：:.、]?\s*)"
)
NON_FRAMEWORK = re.compile(r"(框架关系|关系总图|本章小结|小结|总览|工具箱一览|^附[：:])")
LINK = re.compile(r"\[\[拆书笔记-《([^》]+)》")

LINK_HEADING = re.compile(r"相关链接|关联笔记|与 vault 已拆同主题书")


def de_number(title: str) -> str:
    return NUM_PREFIX.sub("", title).strip().strip("：:。 ")


def parse_frontmatter(lines):
    """返回 (meta_dict, body_start_index)。无 frontmatter 时 meta 为空。"""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return meta, i + 1
        m = re.match(r"^(书名|作者|出版年份)\s*:\s*(.+)$", lines[i])
        if m:
            meta[m.group(1)] = m.group(2).strip().strip("'\"")
    return meta, 0


def first_core_line(lines, start):
    """H3 标题行之后第一个可用作「一句话内核」的行。跳过空行/嵌套标题/
    参见引用/表格行/fenced block 内容；以冒号结尾的引导行只作兜底。"""
    in_fence = False
    fallback = ""
    for j in range(start, len(lines)):
        line = lines[j].rstrip()
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip():
            continue
        s = line.strip()
        if s.startswith(("#", ">", "|", "![", "- [ ]", "```")):
            continue
        text = re.sub(r"\*\*", "", s).strip()
        text = re.sub(r"^[-*]\s+", "", text).strip()
        if not text:
            continue
        if text.endswith(("：", ":")):
            if not fallback:
                fallback = text[:130]
            continue
        return text[:130]
    return fallback


def parse_file(path: Path):
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    meta, body_start = parse_frontmatter(lines)

    book = meta.get("书名") or ""
    m = re.search(r"《([^》]+)》", path.name)
    if not book and m:
        book = m.group(1)
    author = meta.get("作者") or ""

    category = "/".join(path.parent.relative_to(VAULT).parts)

    sections = {}  # de_numbered H2 -> dict(lines, start)
    order = []
    for i in range(body_start, len(lines)):
        m2 = H2.match(lines[i])
        if m2:
            key = de_number(m2.group(1))
            sections[key] = {"start": i + 1, "lines": []}
            order.append(key)

    def between(sec_key):
        """返回该 H2 节内的所有行（到下一个 H2 为止）。"""
        hits = [k for k in order if sec_key in k]
        if not hits:
            return None
        key = hits[0]
        start = sections[key]["start"]
        end = len(lines)
        for k in order[order.index(key) + 1:]:
            # 找到下一个 H2 在原文件中的行号
            pass
        # 重新扫一遍拿行号
        idx = order.index(key)
        next_idx = idx + 1
        # 重新定位各 H2 的行号
        h2_lines = [i for i in range(body_start, len(lines)) if H2.match(lines[i])]
        h2_keys = [de_number(H2.match(lines[i]).group(1)) for i in h2_lines]
        pos = h2_keys.index(next((k for k in h2_keys if sec_key in k), None))
        start = h2_lines[pos] + 1
        end = h2_lines[pos + 1] if pos + 1 < len(h2_lines) else len(lines)
        return lines[start:end]

    frameworks = []
    fw_lines = between("思维框架")
    if fw_lines:
        in_fence = False
        cur = None
        for i, line in enumerate(fw_lines):
            if FENCE.match(line.strip()):
                in_fence = not in_fence
                continue
            m3 = H3.match(line) if not in_fence else None
            if m3:
                name = de_number(m3.group(1))
                if cur:
                    frameworks.append(cur)
                if not name or NON_FRAMEWORK.search(name):
                    cur = None
                    continue
                cur = {"name": name, "core": ""}
            elif cur is not None and not cur["core"]:
                # 在当前框架内找内核行：需要在原 lines 里定位
                pass
        if cur:
            frameworks.append(cur)
        # 第二遍：拿每个框架的 core（借助全文行号重扫，简单起见按 H3 在 fw_lines 内的
        # 相对位置向后找）
        cur_name = None
        in_fence = False
        for line in fw_lines:
            if FENCE.match(line.strip()):
                in_fence = not in_fence
                continue
            m3 = H3.match(line) if not in_fence else None
            if m3:
                name = de_number(m3.group(1))
                cur_name = name if (name and not NON_FRAMEWORK.search(name)) else None
                continue
        cur_name = None
        in_fence = False
        for line in fw_lines:
            if FENCE.match(line.strip()):
                in_fence = not in_fence
                continue
            m3 = H3.match(line) if not in_fence else None
            if m3:
                name = de_number(m3.group(1))
                cur_name = name if (name and not NON_FRAMEWORK.search(name)) else None
                continue
            if cur_name:
                for fw in frameworks:
                    if fw["name"] == cur_name and not fw["core"]:
                        if in_fence:
                            # ASCII 框图兜底：去制表线取首行含中文的文字
                            t = re.sub(r"[│┃┌┐└┘├┤┬┴┼─━]+", "", line).strip()
                            if 6 <= len(t) <= 60 and re.search(r"[\u4e00-\u9fff]", t):
                                fw["core"] = t[:130]
                            break
                        s = line.strip()
                        if s and not s.startswith(("#", ">", "|", "![", "- [ ]", "```")):
                            t = re.sub(r"\*\*", "", re.sub(r"^[-*]\s+", "", s)).strip()
                            fw["core"] = t.rstrip("：:")[:130]
                        break

    counter = []
    ci_lines = between("反常识")
    if ci_lines:
        cur = None
        for line in ci_lines:
            m3 = H3.match(line)
            if m3:
                if cur:
                    counter.append(cur)
                title = de_number(m3.group(1))
                cur = {"title": title, "claim": ""} if title else None
                continue
            if cur is not None:
                s = line.strip()
                if s.startswith(">") and ("大众认知" in s or "作者" in s):
                    piece = re.sub(r"^>\s*", "", s)
                    cur["claim"] = (cur["claim"] + " " + piece).strip()[:200]
                elif s.startswith("#"):
                    break
        if cur:
            counter.append(cur)

    takeaway = ""
    tk_lines = between("一句话总结")
    if tk_lines:
        for line in tk_lines:
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            s = re.sub(r"^>\s*|^\*\*|\*\*$", "", s).strip()
            if s:
                takeaway = s[:150]
                break

    links = []
    for k in order:
        if LINK_HEADING.search(k):
            for line in between(k) or []:
                for name in LINK.findall(line):
                    if name not in links:
                        links.append(name)

    return {
        "book": book,
        "author": author,
        "category": category,
        "file": str(path.relative_to(VAULT)),
        "frameworks": frameworks,
        "counterintuitive": counter,
        "takeaway": takeaway,
        "links": links,
    }


def main():
    files = sorted(VAULT.rglob("拆书笔记-《*.md"))
    records, empty_fw, no_ci = [], [], []
    for p in files:
        try:
            r = parse_file(p)
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] {p.name}: {e}", file=sys.stderr)
            continue
        records.append(r)
        if not r["frameworks"]:
            empty_fw.append(r["file"])
        if not r["counterintuitive"]:
            no_ci.append(r["book"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"generated": "parse_vault_frameworks.py", "count": len(records),
             "books": records},
            f, allow_unicode=True, sort_keys=False, width=200,
        )

    total_fw = sum(len(r["frameworks"]) for r in records)
    total_ci = sum(len(r["counterintuitive"]) for r in records)
    print(f"files={len(records)} frameworks={total_fw} counterintuitive={total_ci}")
    print(f"no-framework ({len(empty_fw)}):")
    for x in empty_fw[:25]:
        print("  -", x)
    print(f"no-counterintuitive ({len(no_ci)}):", "、".join(no_ci[:10]))


if __name__ == "__main__":
    main()
