# -*- coding: utf-8 -*-
"""v31f：新增 Thibeault 低秩假设条目（id=33），并把正文 [15] 改为 [33]。"""
import io, ast

P = r"E:\deepseekworkspace\ncs_v6\make_manuscript_v26_jcp2.py"
L = io.open(P, encoding="utf-8").read().split("\n")

# 1) 在 REFS 块末尾（行 342 的 ']'）之前插入新条目
assert L[342].strip() == "]", L[342]
NEW = (' (33, "Thibeault, V., Allard, A. & Desrosiers, P. The low-rank hypothesis of complex "\n'
       '  "systems. Nat. Phys. 20, 294\\u2013302 (2024).", 2024, "doi", "10.1038/s41567-023-02272-4", False),')
L.insert(342, NEW)
print("ok   Thibeault 条目已插入 (id=33)")

# 2) 正文中的 [15] -> [33]
s = "\n".join(L)
old = '"decrease rapidly, so that an effective rank well below the matrix dimension suffices "\n "'
i = s.find("decrease rapidly, so that an effective rank well below the matrix dimension suffices")
assert i > 0
j = s.find("[15]", i)
assert j > 0 and j - i < 200, (i, j)
s = s[:j] + "[33]" + s[j + 4:]
print("ok   正文 [15] -> [33]")

ast.parse(s)
io.open(P, "w", encoding="utf-8").write(s)
print("语法 OK")
