# -*- coding: utf-8 -*-
"""核实 SRS 的证据基础与稿件是否遗漏标准方法。"""
import io, json, os, re
from collections import Counter

print("=" * 92)
print("① SRS 基线的系统清单")
print("=" * 92)
j = json.load(io.open(r"E:\deepseekworkspace\experiments_v12\v18_srs_final.json", encoding="utf-8"))
rows = j["rows"]
print(f"  总组数 {len(rows)}")
print(f"  kind : {dict(Counter(r['kind'] for r in rows))}")
print(f"  n    : {dict(Counter(r['n'] for r in rows))}")
print(f"  M    : {dict(Counter(r['M'] for r in rows))}")
print(f"  param: {sorted(set(r['param'] for r in rows))}")
print()
print("  * 全部为**合成**：C 的特征值按公式指定，K = 对角 + 小随机扰动")
print("  * **没有任何真实系统**（Lorenz/KS/NS/SST）进入 SRS 比较")
print(f"  * 每格仅 1 个随机种子（80 组 = 2 kind × 5 param × 2 n × 4 M）")

print()
print("=" * 92)
print("② 稿件是否引用秩选择的标准方法？")
print("=" * 92)
s = io.open(r"E:\deepseekworkspace\ncs_v6\make_manuscript_v18_jcp.py", encoding="utf-8").read()
for pat in ("Gavish", "Donoho", "shrinkage", "hard threshold", "AIC", "BIC",
            "scree", "information criterion", "cross validation", "cross-validation"):
    print(f"  {pat!r:24}: {s.count(pat)} 次")

print()
print("=" * 92)
print("③ SRS 的计算节省是如何表述的？")
print("=" * 92)
for pat in (r"one model fit", r"twenty", r"factor of ten", r"training run"):
    for m in list(re.finditer(pat, s))[:2]:
        a = max(0, m.start() - 130); b = min(len(s), m.end() + 130)
        print(f"  [{pat}] ...{' '.join(s[a:b].split())[:230]}...")

print()
print("=" * 92)
print("④ 文献库中的秩选择标准方法（SRS 未比较的）")
print("=" * 92)
D = r"E:\deepseekworkspace\lit_review"
for fn, pat, desc in (
    ("Thibeault(2024)_low_rank_hypothesis.txt", r"scree",
     "有效秩的 scree-plot 解释（srank/nrank/erank 泛函族）"),
    ("Science2024_machine_learning_chaotic_dynamics_dimension.txt", r"Gavish",
     "Gavish–Donoho 最优奇异值收缩（标准秩估计）"),
    ("Theiler1993_dont_bleach.txt", r"AIC",
     "AIC/Schwarz 准则用于嵌入维数选择"),
):
    p = os.path.join(D, fn)
    if not os.path.exists(p):
        print(f"  [缺] {fn}")
        continue
    t = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(pat, t, re.I)
    print(f"  · {desc}")
    if m:
        a = max(0, m.start() - 200); b = min(len(t), m.end() + 350)
        print(f"      {' '.join(t[a:b].split())[:420]}")
    print()
