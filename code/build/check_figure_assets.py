# -*- coding: utf-8 -*-
"""定位：哪些图注没有对应图片；哪些 media 未被引用。"""
import io, re, zipfile
from docx import Document
from docx.table import Table

P = r"E:\deepseekworkspace\manuscript_JCP_v42.docx"
d = Document(P)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}pic"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"


def fe(el):
    return "".join((n.text or "") for n in el.iter() if n.tag in (W + "t", M + "t"))


# 文档顺序
seq = []
for k, ch in enumerate(d.element.body.iterchildren()):
    tag = ch.tag.split('}')[-1]
    if tag == 'p':
        seq.append(('P', fe(ch).strip(), k, ch))
    elif tag == 'tbl':
        tb = Table(ch, d)
        seq.append(('T', f"{len(tb.rows)}x{len(tb.columns)}", k, ch))

# 每个图注 -> 其后最近的图片
print("=" * 104)
print("图注 → 其后图片的对应关系")
print("=" * 104)
figcap = [i for i, (kind, t, k, ch) in enumerate(seq)
          if kind == 'P' and re.match(r'^Fig\. \d+ \|', t)]
for i in figcap:
    n = int(re.match(r'^Fig\. (\d+) \|', seq[i][1]).group(1))
    # 向后找图片（最多 6 个元素）
    found = None
    for j in range(i + 1, min(len(seq), i + 8)):
        pics = list(seq[j][3].iter(PIC))
        if pics:
            found = (j, seq[j][2], len(pics))
            break
    status = f"图片@元素{found[1]}" if found else "**无图片**"
    print(f"  Fig. {n:<3} 图注@元素{seq[i][2]:<5} -> {status}")

# 图片的实际 r:embed
print("\n" + "=" * 104)
print("每个图片引用的 media 文件")
print("=" * 104)
used = []
for k, ch in enumerate(d.element.body.iterchildren()):
    if ch.tag.split('}')[-1] != 'p':
        continue
    for blip in ch.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
        rid = blip.get(R)
        if rid:
            part = d.part.rels[rid].target_ref
            used.append(part)
            print(f"  元素 {k}: {part}")
print(f"\n  被引用 media 数: {len(used)}  去重: {len(set(used))}")

z = zipfile.ZipFile(P)
allm = sorted(x for x in z.namelist() if x.startswith('word/media/'))
un = [x for x in allm if x not in used]
print(f"\n  未被引用的 media（孤儿文件）: {un}")
print(f"\n  总计 media {len(allm)} 个，被引用 {len(set(used))} 个")
