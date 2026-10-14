# -*- coding: utf-8 -*-
"""完整提取段落文本（含 OMML 数学），用于真实审查。"""
import io, re, zipfile
from docx import Document

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def para_full_text(p):
    """段落全文 = 普通 run + OMML 内的 m:t 文本。"""
    parts = []
    for node in p._element.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == M + "t":
            parts.append(node.text or "")
    return "".join(parts)


d = Document(r"E:\deepseekworkspace\manuscript_JCP_v28.docx")
ps = d.paragraphs
print("=" * 100)
print("含数学的图注（前 3 个）")
print("=" * 100)
n = 0
for i, p in enumerate(ps):
    t = para_full_text(p).strip()
    if t.startswith("Figure ") and "|" in t:
        n += 1
        print(f"\n[{i}] {t}")
        if n >= 3:
            break

print("\n" + "=" * 100)
print("符号统计（含数学）")
print("=" * 100)
full = "\n".join(para_full_text(p) for p in ps)
for ch, name in [("\u03c3", "sigma"), ("\u03b1", "alpha"), ("\u03b5", "epsilon"),
                 ("\u03b2", "beta"), ("\u0394", "Delta"), ("\u03bb", "lambda"),
                 ("\u03bc", "mu"), ("\u223c", "sim")]:
    print(f"  {name:<9} {full.count(ch):>4} 次")
