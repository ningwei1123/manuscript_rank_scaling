# -*- coding: utf-8 -*-
"""修正审计脚本的文本提取：纳入 OMML 数学（m:t）。"""
import io

p = r"E:\deepseekworkspace\verify_v6\audit_numbers_v13.py"
t = io.open(p, encoding="utf-8").read()

OLD = 'body = " ".join(p.text for p in doc.paragraphs)'
NEW = (
 '# 文本提取：同时纳入普通 run（w:t）与 OMML 数学（m:t）\n'
 '_WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"\n'
 '_MNS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"\n'
 'def _fulltext(p):\n'
 '    return "".join((n.text or "") for n in p._element.iter() if n.tag in (_WNS + "t", _MNS + "t"))\n'
 'body = " ".join(_fulltext(p) for p in doc.paragraphs)'
)
if OLD in t:
    t = t.replace(OLD, NEW)
    io.open(p, "w", encoding="utf-8").write(t)
    print("已替换文本提取方式（纳入数学）")
else:
    print("[未找到目标行]")
