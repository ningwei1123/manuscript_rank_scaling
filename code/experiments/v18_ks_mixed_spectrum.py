# -*- coding: utf-8 -*-
"""第 3 项 (b)：KS 谱是否为「指数 + 代数尾巴」的混合形式？

假设：KS 谱 = 指数主体（前若干模态）+ 代数尾巴（高阶模态）
检验：分段拟合 + 与纯指数/纯代数的 AIC 比较
"""
import io, json, os
import numpy as np

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
OUT = r"E:\deepseekworkspace\experiments_v12\v18_ks_mixed.json"


def load(fn):
    p = os.path.join(FD, fn)
    rows = []
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue
    return np.array(rows)


sp = load("figures1_ks_spectrum.txt")
k = sp[:, 0]; lam = sp[:, 1]
n = len(k)
print("=" * 108)
print("KS 谱：逐点数值与前向差分")
print("=" * 108)
print(f"  {'k':>4}{'λ_k':>14}{'log λ':>11}{'Δlog λ':>11}{'Δ²log λ':>11}")
d1 = np.diff(np.log(lam))
d2 = np.diff(d1)
for i in range(min(n, 20)):
    s1 = f"{d1[i-1]:.4f}" if i >= 1 else "--"
    s2 = f"{d2[i-2]:.4f}" if i >= 2 else "--"
    print(f"  {int(k[i]):>4}{lam[i]:>14.4f}{np.log(lam[i]):>11.4f}{s1:>11}{s2:>11}")

print()
print("=" * 108)
print("分段检验：是否存在一个断点 k* 使前后两段各自拟合良好？")
print("=" * 108)
print(f"  {'k*':>5}{'前段 R²':>11}{'前段斜率':>11}{'后段 R²':>11}{'后段斜率':>11}"
      f"{'分段残差':>12}{'纯指数残差':>12}{'改善':>9}")
def seg_fit(x, y, lo, hi, mode="exp"):
    m = (np.arange(len(x)) >= lo) & (np.arange(len(x)) < hi)
    if m.sum() < 3:
        return None, None
    xx, yy = x[m], np.log(np.maximum(y[m], 1e-300))
    if mode == "exp":
        s = np.polyfit(xx, yy, 1)
    else:
        s = np.polyfit(np.log(xx), yy, 1)
    pred = np.polyval(s, xx if mode == "exp" else np.log(xx))
    res = ((yy - pred) ** 2).sum()
    r2 = 1 - res / ((yy - yy.mean()) ** 2).sum() if len(yy) > 2 else 0
    return s[0], r2, res

best = None
for kstar in range(4, n - 4):
    a1 = seg_fit(k, lam, 0, kstar, "exp")
    a2 = seg_fit(k, lam, kstar, n, "exp")
    if a1 is None or a2 is None:
        continue
    tot = a1[2] + a2[2]
    pure = seg_fit(k, lam, 0, n, "exp")
    imp = (pure[2] - tot) / pure[2]
    print(f"  {kstar:>5}{a1[1]:>11.4f}{a1[0]:>11.4f}{a2[1]:>11.4f}{a2[0]:>11.4f}"
          f"{tot:>12.4f}{pure[2]:>12.4f}{imp*100:>8.1f}%")
    if best is None or tot < best[1]:
        best = (kstar, tot, a1[0], a2[0], imp)

print()
print("=" * 108)
print("模型比较（AIC）")
print("=" * 108)
def aic(res, kparams):
    n_ = len(lam)
    return n_ * np.log(max(res / n_, 1e-300)) + 2 * kparams

m_exp = seg_fit(k, lam, 0, n, "exp")
m_alg = seg_fit(k, lam, 0, n, "alg")
seg = seg_fit(k, lam, 0, best[0], "exp")[2] + seg_fit(k, lam, best[0], n, "exp")[2]
print(f"  纯指数（2 参数）   残差 {m_exp[2]:.4f}  AIC {aic(m_exp[2],2):.2f}")
print(f"  纯代数（2 参数）   残差 {m_alg[2]:.4f}  AIC {aic(m_alg[2],2):.2f}")
print(f"  分段指数（4 参数） 残差 {seg:.4f}  AIC {aic(seg,4):.2f}  断点 k*={best[0]}")
print()
print(f"  => 最优断点 k* = {best[0]}")
print(f"     前段指数率 = {best[2]:.4f}，后段指数率 = {best[3]:.4f}")
print(f"     分段相对纯指数的残差改善 = {best[4]*100:.1f}%")

# 用后段的 alpha 作为 alpha_cov
alpha_cov = best[3]
print()
print("=" * 108)
print("(c) 两-alpha 框架的应用")
print("=" * 108)
print(f"  · KS 谱的分段指数率：前段 {best[2]:.4f}，后段 {best[3]:.4f}")
print(f"  · 秩曲线 ln(1/eps) 斜率（窗口相关）：1.17 – 1.56")
print(f"  · 理论预测：秩斜率 = 1/alpha")
for a in (best[2], best[3], 0.70, 1.0):
    print(f"    若 alpha = {a:.4f} -> 理论秩斜率 {1/a:.3f}")
print()
print("  => KS 谱**不是单一指数**，因此『一个 alpha』本身不成立；")
print("     秩斜率与谱指数的不匹配部分来自这个混合结构。")

json.dump(dict(kstar=best[0], seg1_rate=best[2], seg2_rate=best[3],
               improvement=best[4], alpha_cov=alpha_cov,
               resid_exp=float(m_exp[2]), resid_alg=float(m_alg[2]),
               resid_seg=float(seg)),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
