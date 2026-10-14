# -*- coding: utf-8 -*-
"""文献启发检索：对齐条件的充要性 / 不对齐时的可算修正项。

数学问题：
  输入尾部 T_in(r) = sum_{k>r} lam_k(C)
  可达误差 T_out(r) = sum_{k>r} lam_k(C_y),  C_y = K C K^T
  已知：K 保持 C 的本征空间 => T_out = T_in（充分）
  问：充要条件是什么？不对齐时能否算修正项？

需要的工具
----------
(1) 本征空间扰动界（Davis-Kahan sin-theta）
(2) 典型相关分析（CCA）/ 白化后的算子范数
(3) Weyl 不等式（特征值扰动）
(4) 算子 norm 与 Frobenius norm 的关系
"""
import io, os, re

D = r"E:\deepseekworkspace\lit_review"
PATS = {
 "Davis-Kahan / sin-theta 本征空间扰动": [
   r"Davis.{0,5}Kahan", r"sin.?theta", r"eigenvector.{0,40}perturbation",
   r"subspace.{0,30}perturbation", r"principal angle"],
 "典型相关 / 白化": [
   r"canonical correlation", r"CCA", r"whiten", r"whitening",
   r"cross.?covariance"],
 "Weyl 不等式 / 特征值扰动": [
   r"Weyl.{0,15}inequality", r"eigenvalue.{0,30}perturbation bound",
   r"interlacing"],
 "算子范数与谱尾部关系": [
   r"tail.{0,30}(norm|sum)", r"residual.{0,30}norm",
   r"operator norm.{0,40}(eigenvalue|spectrum)"],
 "对齐 / 不变子空间": [
   r"invariant subspace", r"commut", r"simultaneous.{0,20}diagonal",
   r"align"],
}
for tag, pats in PATS.items():
    print("=" * 106)
    print(tag)
    print("=" * 106)
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
                a = max(0, h.start() - 160); b = min(len(s), h.end() + 340)
                print(f"  [{fn[:40]:<40}] {' '.join(s[a:b].split())[:310]}")
                break
    if not hits:
        print("  （无匹配）")
    print()
