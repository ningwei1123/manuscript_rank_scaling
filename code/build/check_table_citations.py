# -*- coding: utf-8 -*-
"""检查全部表格：正文引用情况 + 引用处的科学解读。"""
import io, re
from docx import Document
from docx.table import Table

P = r"E:\deepseekworkspace\manuscript_JCP_v44.docx"
d = Document(P)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def fe(el):
    return "".join((n.text or "") for n in el.iter() if n.tag in (W + "t", M + "t"))


# 文档顺序
IT = []
for ch in d.element.body.iterchildren():
    tag = ch.tag.split('}')[-1]
    if tag == 'p':
        IT.append(('P', fe(ch).strip(), ch))
    elif tag == 'tbl':
        tb = Table(ch, d)
        IT.append(('T', f"{len(tb.rows)}x{len(tb.columns)}", ch))

print("=" * 106)
print("① 每张表的标题、表头、引用情况")
print("=" * 106)
for n in range(1, 7):
    capk = next((k for k, (kind, t, ch) in enumerate(IT)
                 if kind == 'P' and re.match(r'^Table %d \|' % n, t)), None)
    if capk is None:
        print(f"\nTable {n}: **无标题**")
        continue
    cap = IT[capk][1]
    # 其后的数据表
    tblk = next((k for k in range(capk + 1, len(IT))
                 if IT[k][0] == 'T' and re.match(r'^\d+x\d+$', IT[k][1])
                 and int(IT[k][1].split('x')[0]) > 1), None)
    print(f"\n{'='*106}")
    print(f"Table {n}  [标题@元素 {IT[capk][2] if False else capk}]")
    print(f"  标题: {cap}")
    if tblk is not None:
        tb = Table(IT[tblk][2], d)
        hdr = [c.text.strip() for c in tb.rows[0].cells]
        print(f"  数据: {len(tb.rows)}x{len(tb.columns)}  表头={hdr}")
    else:
        print(f"  数据: **未找到数据表**")
    # 引用
    cites = [(k, IT[k][1]) for k in range(len(IT))
             if k != capk and IT[k][0] == 'P' and re.search(r'\bTable\s*%d\b' % n, IT[k][1])]
    print(f"  正文引用: {len(cites)} 处")
    for k, t in cites:
        idx = t.find(f"Table {n}")
        a = max(0, idx - 190)
        print(f"      [{k}] ...{t[a:idx+250]}...")
