# -*- coding: utf-8 -*-
"""Burgers：定量核对——有效 alpha 与谱指数是否一致？

这是对 KS 19% 偏差的**独立重复**：
  · 若 alpha_eff ≈ alpha_cov，则秩律定量成立，偏差只是判类阈值问题
  · 若 alpha_eff << alpha_cov，则秩律在真实非线性 PDE 上系统性失效
"""
import io, json, os
import numpy as np
import h5py

D = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
OUT = r"E:\deepseekworkspace\experiments_v12\v19_burgers_alpha.json"


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def fit_alpha_spec(lam, kmin=3):
    """谱的指数拟合率（全谱）。"""
    lam = np.sort(lam)[::-1]
    k = np.arange(1, len(lam) + 1); m = k >= kmin
    le = np.log(np.maximum(lam[m], 1e-300))
    s = np.polyfit(k[m], le, 1)
    return float(-s[0])


def fit_beta_spec(lam, kmin=3):
    lam = np.sort(lam)[::-1]
    k = np.arange(1, len(lam) + 1); m = k >= kmin
    le = np.log(np.maximum(lam[m], 1e-300))
    s = np.polyfit(np.log(k[m]), le, 1)
    return float(-s[0])


def r_closed(a, eps, n):
    return (1 / (2 * a)) * np.log(1.0 / np.maximum(eps ** 2 * (1 - np.exp(-2 * a * n)), 1e-300))


def fit_alpha_eff(eps, r, n, lo=0.05, hi=5.0):
    grid = np.linspace(lo, hi, 2000)
    best, be = None, np.inf
    for a in grid:
        e = ((r_closed(a, eps, n) - r) ** 2).sum()
        if e < be:
            be, best = e, a
    return float(best), float(be)


p = os.path.join(D, "1D_Burgers_Sols_Nu0.01.hdf5")
print("=" * 112)
print("Burgers (Nu=0.01)：有效 alpha vs 谱指数")
print("=" * 112)

with h5py.File(p, "r") as f:
    ten = f["tensor"]
    ntr, nt, nx = ten.shape
    N = 16
    eps_grid = np.logspace(np.log10(0.3), np.log10(1e-4), 60)
    rows = []
    print(f"  {'轨迹':>5}{'α_谱':>10}{'β_谱':>10}{'α_eff':>10}{'α_eff/α_谱':>13}"
          f"{'r(1e-3)':>9}{'r(1e-6)':>9}")
    for i in range(N):
        field = np.asarray(ten[i], dtype=np.float64)
        Y = field - field.mean(0, keepdims=True)
        sv = np.linalg.svd(Y, compute_uv=False)
        lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
        n = len(lam)
        a_s = fit_alpha_spec(lam)
        b_s = fit_beta_spec(lam)
        r = ranks(lam, eps_grid)
        a_e, err = fit_alpha_eff(eps_grid, r, n)
        rows.append(dict(traj=i, a_spec=a_s, b_spec=b_s, a_eff=a_e,
                         ratio=(a_e / a_s if a_s > 0 else np.nan),
                         r1e3=float(ranks(lam, [1e-3])[0]),
                         r1e6=float(ranks(lam, [1e-6])[0])))
        if i < 12:
            print(f"  {i:>5}{a_s:>10.4f}{b_s:>10.4f}{a_e:>10.4f}"
                  f"{(a_e/a_s if a_s>0 else float('nan')):>13.4f}"
                  f"{rows[-1]['r1e3']:>9.0f}{rows[-1]['r1e6']:>9.0f}")

    rs = np.array([x["ratio"] for x in rows if np.isfinite(x["ratio"])])
    print()
    print("=" * 112)
    print("判读")
    print("=" * 112)
    print(f"  α_eff / α_谱 的比: 中位 {np.median(rs):.4f}  范围 {rs.min():.4f} .. {rs.max():.4f}")
    print()
    if abs(np.median(rs) - 1) < 0.2:
        print("  => α_eff ≈ α_谱：秩律在 Burgers 上**定量成立**")
    elif np.median(rs) < 0.5:
        print("  => α_eff << α_谱：秩曲线比谱预测**平缓得多**")
        print("     => 与 KS 的 19% 偏差**同一机制**，且在真实非线性 PDE 上更严重")
    else:
        print("  => 介于两者之间")

    # 与 KS 对照
    print()
    print("  与 Kuramoto-Sivashinsky 的对照：")
    print(f"    KS   : a_eff = 0.53-0.67,  全谱 α = 0.705  -> 比 ≈ 0.75-0.95")
    print(f"    Burgers: a_eff/α 中位 = {np.median(rs):.4f}")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
