# -*- coding: utf-8 -*-
"""文献检索：为五个方向分别定位本机 PDF 中的关键依据。"""
import io, os, re

D = r"E:\deepseekworkspace\lit_review"

NEEDS = {
 "方向 C 非可逆 / 等距 / Wold 分解": [
   r"Wold decomposition", r"isometry.{0,60}(unitary|shift)",
   r"non.?invertible", r"expanding map.{0,60}Koopman",
   r"Koopman.{0,40}isometry", r"measure.preserving.{0,50}(unitary|isometry)"],
 "方向 B 主角度 / 本征空间扰动": [
   r"principal angle", r"Davis.{0,5}Kahan", r"sin.?theta",
   r"subspace.{0,30}(angle|perturbation)", r"canonical correlation"],
 "方向 D 相关函数衰减 -> 协方差谱": [
   r"decay of correlation", r"exponential decay.{0,40}correlation",
   r"covariance.{0,30}(decay|spectrum)", r"mixing rate",
   r"summab", r"polynomial decay"],
 "方向 A 传递算子谱 -> 可观测量": [
   r"transfer operator.{0,50}(spectrum|eigenvalue)",
   r"resonance.{0,50}observable", r"autocorrelation.{0,50}spectrum",
   r"spectral decomposition.{0,60}correlation", r"Koopman mode"],
 "方向 E 样本量 / 最优秩": [
   r"optimal.{0,30}(rank|dimension).{0,40}sample", r"sample.{0,30}rank.{0,30}scaling",
   r"bias.variance.{0,40}(rank|dimension)", r"n.{0,3}\*.{0,10}\(m\)"],
}
for tag, pats in NEEDS.items():
    print("=" * 108)
    print(tag)
    print("=" * 108)
    n = 0
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".txt"):
            continue
        s = io.open(os.path.join(D, fn), encoding="utf-8", errors="replace").read()
        best = None
        for pat in pats:
            m = list(re.finditer(pat, s, re.I))
            if m:
                best = (pat, m[0])
                break
        if best:
            n += 1
            pat, h = best
            a = max(0, h.start() - 170); b = min(len(s), h.end() + 380)
            print(f"  [{fn[:38]:<38}|{pat[:22]:<22}] {' '.join(s[a:b].split())[:330]}")
    if n == 0:
        print("  （无匹配）")
    print()
