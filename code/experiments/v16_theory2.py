# -*- coding: utf-8 -*-
"""V16 推导验证（修正版）：只在**未饱和**的窗口内拟合。

关键修正：r(ε) 在 ε ≤ ε_c 时饱和为 n。若把饱和点纳入拟合，
幂指数/对数斜率会被严重低估（首轮脚本即犯此错）。
"""
import json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12"


def r_curve(lam, eps):
    lam = np.asarray(lam, float)
    e2 = lam ** 2
    tail = np.cumsum(e2[::-1])[::-1]
    rel = np.sqrt(np.maximum(tail / e2.sum(), 0))
    return np.minimum(np.array([min(int(np.searchsorted(-rel, -e)) + 1, len(lam))
                                for e in eps], float), len(lam))


def fit_unsat(eps, r, kind="log"):
    """只用 r < r_max 的点（未饱和）。"""
    m = (r > 0) & (r < r.max())
    if m.sum() < 6:
        return np.nan, np.nan, 0
    if kind == "log":
        y, x = r[m], np.log(1 / eps[m])
        sl, ic = np.polyfit(x, y, 1)
        r2 = 1 - ((y - (sl * x + ic)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        return sl, r2, int(m.sum())
    else:
        y, x = np.log(r[m]), np.log(eps[m])
        p, c = np.polyfit(x, y, 1)
        r2 = 1 - ((y - (p * x + c)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        return -p, r2, int(m.sum())


eps = np.logspace(-1, -10, 100)
RES = {}
print("=" * 104)
print("修正验证：仅未饱和窗口")
print("=" * 104)

# 取 n 足够大，使饱和阈值 ε_c = 1/n 远小于拟合下界
n = 5000

print("\n【II 指数类】λ_k = e^{−α(k−1)}   预测 r(ε) 斜率 = 1/α")
print(f"  {'α':>6}{'1/α 预测':>10}{'实测斜率':>10}{'偏差':>8}{'R²':>8}{'未饱和点':>9}")
for alpha in (0.005, 0.01, 0.02, 0.05, 0.10, 0.20):
    lam = np.exp(-alpha * np.arange(n))
    r = r_curve(lam, eps)
    sl, r2, np_ = fit_unsat(eps, r, "log")
    RES[f"exp_{alpha}"] = dict(alpha=alpha, pred=1 / alpha, slope=float(sl),
                               dev=float(abs(sl - 1 / alpha) / (1 / alpha)), R2=float(r2), npts=np_)
    print(f"  {alpha:>6.3f}{1/alpha:>10.2f}{sl:>10.3f}{abs(sl-1/alpha)/(1/alpha)*100:>7.2f}%"
          f"{r2:>8.4f}{np_:>9d}")

print("\n【III 代数类】λ_k = k^{−β}   预测 r(ε) ~ ε^{−1/(β−1/2)}")
print(f"  {'β':>6}{'1/(β−1/2) 预测':>16}{'实测幂指数':>12}{'偏差':>9}{'R²':>8}{'未饱和点':>9}")
for beta in (0.55, 0.6, 0.75, 1.0, 1.5, 2.0, 3.0):
    lam = (np.arange(1, n + 1)) ** (-beta)
    r = r_curve(lam, eps)
    p, r2, np_ = fit_unsat(eps, r, "pow")
    pred = 1 / (beta - 0.5)
    RES[f"alg_{beta}"] = dict(beta=beta, pred=float(pred), measured=float(p),
                              dev=float(abs(p - pred) / pred), R2=float(r2), npts=np_)
    print(f"  {beta:>6.2f}{pred:>16.3f}{p:>12.3f}{abs(p-pred)/pred*100:>8.1f}%{r2:>8.4f}{np_:>9d}")

print("\n【I 近平坦类】λ_k ∈ [1−δ, 1]   预测：r(ε) 缓变，非对数、非幂律")
print(f"  {'δ':>7}{'ρ=λ_n/λ_1':>11}{'α_*（拟合）':>12}{'r(1e-1)':>9}{'r(1e-6)':>9}"
      f"{'变化倍数':>10}{'对数斜率':>10}")
for delta in (0.0, 0.05, 0.2, 0.5, 0.8, 0.95):
    lam = 1 - delta * (np.arange(n) / (n - 1))
    r = r_curve(lam, eps)
    k = np.arange(1, n + 1)
    m = (k >= max(2, n // 10)) & (k <= max(6, int(0.8 * n)))
    a = -np.polyfit(k[m], np.log(lam[m]), 1)[0] if m.sum() > 5 else np.nan
    i1 = int(np.argmin(abs(eps - 1e-1))); i6 = int(np.argmin(abs(eps - 1e-6)))
    sl, r2, np_ = fit_unsat(eps, r, "log")
    RES[f"flat_{delta}"] = dict(delta=delta, rho=float(lam[-1] / lam[0]), alpha=float(a),
                                r_1e1=float(r[i1]), r_1e6=float(r[i6]),
                                ratio=float(r[i6] / max(r[i1], 1)), slope=float(sl))
    print(f"  {delta:>7.2f}{lam[-1]/lam[0]:>11.3f}{a:>12.5f}{r[i1]:>9.0f}{r[i6]:>9.0f}"
          f"{r[i6]/max(r[i1],1):>10.2f}{sl:>10.3f}")

json.dump(RES, open(os.path.join(OUT, "v16_theory_classes.json"), "w", encoding="utf-8"), indent=2)
print("\nsaved v16_theory_classes.json")
