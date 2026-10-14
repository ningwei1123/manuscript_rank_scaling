# -*- coding: utf-8 -*-
"""代数分支实例（修正版）：正确的 AR(1) 幅度标定。

稳态方差：Var(u_k) = sigma_k² / (1 - a²)
欲得 λ_k = k^{-2β}（特征值），取 sigma_k = k^{-β}·sqrt(1-a²)。
（先前写成 k**(-2*beta)**0.5，实际等于 k^{-beta}，但因运算符优先级
 被解析为 k**((-2β)**0.5)，产生复数并破坏了谱。）
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v11_alg_FINAL.json"
rng = np.random.default_rng(20261113)


def cov_spectrum(X):
    Y = X - X.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / max(len(Y) - 1, 1)


def measure(lam, kfit, r_lo=5, r_hi_frac=0.10, n_pts=500):
    lam = np.sort(lam)[::-1]; n = len(lam)
    k = np.arange(1, n + 1); lo, hi = kfit; hi = hi or n
    sel = (k >= lo) & (k <= hi) & (lam > 0)
    ps = np.polyfit(np.log(k[sel]), np.log(lam[sel]), 1)
    spec_r2 = 1 - ((np.log(lam[sel]) - np.polyval(ps, np.log(k[sel]))) ** 2).sum() / \
                   ((np.log(lam[sel]) - np.log(lam[sel]).mean()) ** 2).sum()
    p = -ps[0]
    e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    eps = np.logspace(np.log10(0.9), np.log10(1e-12), n_pts)
    r = np.array([int(np.searchsorted(-rel, -e)) + 1 for e in eps], float)
    m = (r >= r_lo) & (r <= n * r_hi_frac)
    if m.sum() < 8:
        return None
    sp = np.polyfit(np.log(1 / eps[m]), np.log(r[m]), 1)
    r2p = 1 - ((np.log(r[m]) - np.polyval(sp, np.log(1 / eps[m]))) ** 2).sum() / \
               ((np.log(r[m]) - np.log(r[m]).mean()) ** 2).sum()
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / \
               ((r[m] - r[m].mean()) ** 2).sum()
    theo = 2 / (2 * p - 1) if p > 0.5 else float("inf")
    return dict(n=n, spec_p=float(p), spec_R2=float(spec_r2),
                eps_exp=float(sp[0]), r2_power=float(r2p), r2_log=float(r2l),
                theo=theo, dev_pct=(sp[0] - theo) / theo * 100 if np.isfinite(theo) else None,
                n_fit=int(m.sum()), r_range=[float(r[m].min()), float(r[m].max())],
                verdict=("POWER" if r2p > r2l + 0.005 else
                         "LOG" if r2l > r2p + 0.005 else "AMBIG"))


def ar1(p_exp, n=4096, n_snap=200000, a=0.9999, burn=3000):
    """稳态协方差 λ_k = k^{-p_exp}。"""
    k = np.arange(1, n + 1, dtype=float)
    sig = k ** (-p_exp / 2) * np.sqrt(1 - a ** 2)   # 使 Var = k^{-p_exp}
    u = np.zeros(n)
    for _ in range(burn):
        u = a * u + sig * rng.standard_normal(n)
    X = np.empty((n_snap, n), dtype=np.float64)
    for i in range(n_snap):
        u = a * u + sig * rng.standard_normal(n)
        X[i] = u
    return X


print("=" * 118)
print("代数分支实例（最终，修正幅度标定）")
print("=" * 118)
print(f"  {'系统':<24}{'λ指数(设定)':>12}{'拟合 p':>9}{'谱R²':>8}{'理论 2/(2p-1)':>15}"
      f"{'实测':>9}{'偏差':>8}{'R²pow':>8}{'R²log':>8}{'判定':>7}")

results = {}
for p_set in (2.0, 2.5, 3.0, 4.0, 5.0):
    X = ar1(p_set)
    lam = cov_spectrum(X)
    a = measure(lam, kfit=(2, 400))
    if a is None:
        print(f"  λ指数={p_set}: 窗口不足"); continue
    results[f"lam_exp_{p_set}"] = dict(a, p_set=p_set)
    print(f"  {'AR(1) 长记忆 λ~k^-'+str(p_set):<24}{p_set:>12.1f}{a['spec_p']:>9.3f}"
          f"{a['spec_R2']:>8.4f}{a['theo']:>15.3f}{a['eps_exp']:>9.3f}"
          f"{a['dev_pct']:>7.1f}%{a['r2_power']:>8.4f}{a['r2_log']:>8.4f}{a['verdict']:>7}")

json.dump(results, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n已保存 {OUT}")
devi = [abs(v["dev_pct"]) for v in results.values()]
if devi:
    print(f"\n理论与实测的最大偏差: {max(devi):.1f}%   中位: {np.median(devi):.1f}%")
print(f"全部判为代数分支(POWER): {all(v['verdict']=='POWER' for v in results.values())}")
