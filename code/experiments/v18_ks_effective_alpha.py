# -*- coding: utf-8 -*-
"""第 3 项 (c) 决定性：从秩-精度曲线**反演**有效的 alpha，并找出用哪一段谱。

方法
----
指数分支的闭式给出 r(eps) = (1/2a) ln[1/(eps^2 (1-e^{-2an}))]。
把它对实测秩曲线做最小二乘（只拟合 a），得到 **a_eff**。
再与以下候选比较：
  · a_全谱（32 个模态整体拟合）
  · a_前段（能量阈值 0.9 的前 8 个模态）
  · 若 a_eff ≈ a_前段  -> 秩曲线由主导能量的谱段决定
  · 若 a_eff ≈ a_全谱  -> 秩曲线由整体拟合决定
"""
import io, json, os
import numpy as np

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
OUT = r"E:\deepseekworkspace\experiments_v12\v18_ks_alpha_eff.json"


def load(fn):
    rows = []
    for line in io.open(os.path.join(FD, fn), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue
    return np.array(rows)


sp = load("figures1_ks_spectrum.txt")
ra = load("figure2_ks_rank_accuracy.txt")
k = sp[:, 0]; lam = sp[:, 1]
eps = ra[:, 0]; r = ra[:, 1]
n_all = len(lam)


def r_closed(a, eps, n):
    return (1 / (2 * a)) * np.log(1.0 / np.maximum(eps ** 2 * (1 - np.exp(-2 * a * n)), 1e-300))


def fit_alpha_eff(eps_w, r_w, n):
    """只拟合 a（网格搜索，稳健）。"""
    grid = np.linspace(0.05, 3.0, 3000)
    best_a, best_err = None, np.inf
    for a in grid:
        pred = r_closed(a, eps_w, n)
        e = ((pred - r_w) ** 2).sum()
        if e < best_err:
            best_err, best_a = e, a
    return float(best_a), float(best_err)


print("=" * 108)
print("从秩-精度曲线反演有效 alpha")
print("=" * 108)
cand = {}
# 全谱
s = np.polyfit(k, np.log(np.maximum(lam, 1e-300)), 1)
cand["全谱(32模态)"] = float(-s[0])
# 前段（多个能量阈值）
cum = np.cumsum(lam) / lam.sum()
for thr in (0.8, 0.9, 0.95, 0.99):
    ks = int(np.searchsorted(cum, thr) + 1)
    m = np.arange(n_all) < ks
    ss = np.polyfit(k[m], np.log(np.maximum(lam[m], 1e-300)), 1)
    cand[f"前段(能量{thr}, {ks}模态)"] = float(-ss[0])
print("  候选 alpha：")
for kk, vv in cand.items():
    print(f"    {kk:<24} alpha = {vv:.4f}")

print()
print(f"  {'eps 窗口':>18}{'a_eff':>10}{'残差':>13}{'最接近的候选':>26}{'相对差':>10}")
res = {}
wins = [(0.3, 1e-4), (0.3, 1e-2), (0.1, 1e-4), (0.05, 1e-4), (0.5, 1e-6), (1.0, 1e-6)]
for lo, hi in wins:
    m = (eps <= lo) & (eps >= hi) & (r > 0)
    if m.sum() < 6:
        continue
    a_eff, err = fit_alpha_eff(eps[m], r[m], n_all)
    # 找最接近的候选
    best_k = min(cand, key=lambda kk: abs(cand[kk] - a_eff))
    rel = (a_eff - cand[best_k]) / cand[best_k] * 100
    res[f"{lo}_{hi}"] = dict(a_eff=a_eff, resid=err, nearest=best_k,
                             nearest_val=cand[best_k], rel_pct=rel, npts=int(m.sum()))
    print(f"  {f'{lo}..{hi}':>18}{a_eff:>10.4f}{err:>13.4e}{best_k:>26}{rel:>9.1f}%")

print()
print("=" * 108)
print("判读")
print("=" * 108)
ae = [v["a_eff"] for v in res.values()]
print(f"  a_eff 范围: {min(ae):.4f} .. {max(ae):.4f}")
nearest = [v["nearest"] for v in res.values()]
from collections import Counter
print(f"  最接近的候选中出现最频繁的: {Counter(nearest).most_common(2)}")
print()
if "前段(能量0.9, 8模态)" in cand:
    print(f"  前段(8 模态) alpha = {cand['前段(能量0.9, 8模态)']:.4f}")
    print(f"  全谱 alpha        = {cand['全谱(32模态)']:.4f}")
    print(f"  => a_eff 更接近哪一段即说明秩曲线由该段支配")

json.dump(dict(candidates=cand, windows=res),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
