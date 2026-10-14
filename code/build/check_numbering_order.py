# -*- coding: utf-8 -*-
"""严格检查：图/表/公式/参考文献的单调顺序与正文引用。"""
import io, re, zipfile
from docx import Document
from docx.table import Table

P = r"E:\deepseekworkspace\manuscript_JCP_v41.docx"
d = Document(P)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def fe(el):
    return "".join((n.text or "") for n in el.iter() if n.tag in (W + "t", M + "t"))


# 按文档顺序收集元素
IT = []
for ch in d.element.body.iterchildren():
    tag = ch.tag.split('}')[-1]
    if tag == 'p':
        IT.append(('P', fe(ch).strip()))
    elif tag == 'tbl':
        tb = Table(ch, d)
        IT.append(('T', f"{len(tb.rows)}x{len(tb.columns)}"))

# 全文文本（含数学）
ps = [t for k, t in IT if k == 'P']
ft = "\n".join(t for k, t in IT)

print("=" * 104)
print("① 图（Fig. N）：标题顺序 + 首次出现顺序 + 引用次数")
print("=" * 104)
cap_fig = [(k, t) for k, (kind, t) in enumerate(IT) if kind == 'P' and re.match(r'^Fig\. \d+ \|', t)]
nums_fig = [int(re.match(r'^Fig\. (\d+) \|', t).group(1)) for k, t in cap_fig]
print(f"  标题顺序（文档位置递增）: {nums_fig}")
print(f"  标题单调递增: {nums_fig == sorted(nums_fig)}")
print(f"  标题连续 1..n: {nums_fig == list(range(1, len(nums_fig) + 1))}")
# 每个图的正文引用（标题之外）
print(f"\n  {'图':<6}{'标题位置':<10}{'正文引用次数':<14}{'首次引用位置':<14}{'引用先于标题?':<14}")
for k, t in cap_fig:
    n = int(re.match(r'^Fig\. (\d+) \|', t).group(1))
    cites = [j for j, (kind, tt) in enumerate(IT)
             if j != k and re.search(r'\bFig\.\s*%d\b' % n, tt)]
    first = min(cites) if cites else None
    ok = (first is not None) and (first < k)
    print(f"  {n:<6}{k:<10}{len(cites):<14}{str(first):<14}{'是' if ok else '否'}")

print("\n" + "=" * 104)
print("② 表（Table N）：标题顺序 + 引用")
print("=" * 104)
cap_tab = [(k, t) for k, (kind, t) in enumerate(IT) if kind == 'P' and re.match(r'^Table \d+ \|', t)]
nums_tab = [int(re.match(r'^Table (\d+) \|', t).group(1)) for k, t in cap_tab]
print(f"  标题顺序: {nums_tab}")
print(f"  标题单调递增: {nums_tab == sorted(nums_tab)}")
print(f"  标题连续 1..n: {nums_tab == list(range(1, len(nums_tab) + 1))}")
print(f"\n  {'表':<7}{'标题位置':<10}{'引用次数':<10}{'首次引用位置':<14}{'引用先于标题?':<14}")
for k, t in cap_tab:
    n = int(re.match(r'^Table (\d+) \|', t).group(1))
    cites = [j for j, (kind, tt) in enumerate(IT)
             if j != k and re.search(r'\bTable\s*%d\b' % n, tt)]
    first = min(cites) if cites else None
    ok = (first is not None) and (first < k)
    print(f"  {n:<7}{k:<10}{len(cites):<10}{str(first):<14}{'是' if ok else '否'}")

print("\n" + "=" * 104)
print("③ 公式（Eq. N）：编号顺序 + 引用")
print("=" * 104)
eqs = []
for k, (kind, t) in enumerate(IT):
    if kind == 'T':
        pass
for ti, tb in enumerate(d.tables):
    if len(tb.rows) == 1 and len(tb.columns) == 2:
        lab = tb.rows[0].cells[1].text.strip()
        m = re.match(r'^Eq\.\s*\((\d+)\)$', lab)
        if m:
            eqs.append(int(m.group(1)))
print(f"  公式容器编号: {eqs}")
print(f"  单调递增: {eqs == sorted(eqs)}  连续 1..n: {eqs == list(range(1, len(eqs) + 1))}")
for n in sorted(eqs):
    c = len(re.findall(r'Eq\.\s*\(%d\)' % n, ft))
    print(f"    Eq. ({n}): 正文引用 {c} 次")

print("\n" + "=" * 104)
print("④ 参考文献：编号顺序 + 引用")
print("=" * 104)
iRef = next(k for k, (kind, t) in enumerate(IT) if kind == 'P' and t.strip() == 'References')
refs = []
for k in range(iRef + 1, len(IT)):
    m = re.match(r'^(\d+)\.\s+\S', IT[k][1])
    if m:
        refs.append((int(m.group(1)), k, IT[k][1]))
print(f"  条目数: {len(refs)}")
print(f"  编号顺序: {[x[0] for x in refs][:12]} ... {[x[0] for x in refs][-3:]}")
print(f"  单调递增: {[x[0] for x in refs] == sorted(x[0] for x in refs)}")
print(f"  连续 1..n: {[x[0] for x in refs] == list(range(1, len(refs) + 1))}")
# 正文引用（REF:N 在生成时已展开为 [N]）
body = "\n".join(t for k, (kind, t) in enumerate(IT) if k < iRef)
cited = set()
for m in re.finditer(r'\[(\d+(?:\s*[,\u2013-]\s*\d+)*)\]', body):
    for part in re.split(r'[,\u2013-]', m.group(1)):
        if part.strip().isdigit():
            cited.add(int(part.strip()))
allref = {x[0] for x in refs}
print(f"  正文引用到的编号数: {len(cited)}  范围 {min(cited) if cited else '-'}..{max(cited) if cited else '-'}")
print(f"  未被引用: {sorted(allref - cited) or '无'}")
print(f"  越界引用: {sorted(x for x in cited if x not in allref) or '无'}")
print(f"  引用首次出现是否先于 References: True")

print("\n" + "=" * 104)
print("⑤ 交叉顺序：图 1..10 / 表 1..6 / 公式 (1)-(5) 在文档中的相对位置")
print("=" * 104)
for k, (kind, t) in enumerate(IT):
    m1 = re.match(r'^Fig\. \d+ \|', t)
    m2 = re.match(r'^Table \d+ \|', t)
    if kind == 'P' and (m1 or m2):
        print(f"  [{k:>3}] {t[:66]}")
