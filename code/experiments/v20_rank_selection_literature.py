# -*- coding: utf-8 -*-
"""核查 SRS 的基线是否遗漏了学界标准方法（这是最可能的审稿人攻击点）。"""
import io, os, re

D = r"E:\deepseekworkspace\lit_review"
print("=" * 100)
print("检索：秩选择 / 截断准则的已有标准方法")
print("=" * 100)
PATS = {
 "AIC/BIC 型秩选择": [r"AIC", r"BIC", r"information criterion", r"model order selection"],
 "Gavish-Donoho / 最优硬阈值": [r"Gavish", r"Donoho", r"optimal hard threshold", r"optimal singular value"],
 "能量/方差准则": [r"energy criterion", r"cumulative energy", r"variance explained", r"scree"],
 "交叉验证型秩选择": [r"cross.validat.{0,40}rank", r"rank.{0,30}cross.validat"],
 "信息论/熵": [r"entropy.{0,30}rank", r"Kolmogorov entropy", r"metric entropy"],
 "自适应秩 / 低秩估计": [r"adaptive rank", r"rank estimation", r"estimating the rank",
                    r"optimal rank", r"rank determination"],
}
for tag, pats in PATS.items():
    print(f"\n--- {tag} ---")
    hits = 0
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".txt"):
            continue
        s = io.open(os.path.join(D, fn), encoding="utf-8", errors="replace").read()
        for pat in pats:
            m = list(re.finditer(pat, s, re.I))
            if m:
                hits += 1
                h = m[0]
                a = max(0, h.start() - 140); b = min(len(s), h.end() + 250)
                print(f"  [{fn[:40]:<40}] {' '.join(s[a:b].split())[:290]}")
                break
    if hits == 0:
        print("  （无匹配）")
