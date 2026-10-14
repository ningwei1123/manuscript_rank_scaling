# -*- coding: utf-8 -*-
"""为代数分支实例准备：数据 txt + 图（300 dpi）。

系统：近中性长记忆随机场（AR(1) 型），稳态协方差 λ_k = k^{-p}，p > 1。
理论：r(ε) ~ ε^{-2/(2p-1)} = ε^{-1/(p-1/2)}。
"""
import io, os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
FIGD = r"E:\nature投稿\探索1\数值验证\figures"
AR = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\artifacts"
os.makedirs(FD, exist_ok=True); os.makedirs(FIGD, exist_ok=True); os.makedirs(AR, exist_ok=True)
rng = np.random.default_rng(20261113)


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def ar1(p_exp, n=4096, n_snap=200000, a=0.9999, burn=3000):
    k = np.arange(1, n + 1, dtype=float)
    sig = k ** (-p_exp / 2) * np.sqrt(1 - a ** 2)
    u = np.zeros(n)
    for _ in range(burn):
        u = a * u + sig * rng.standard_normal(n)
    X = np.empty((n_snap, n))
    for i in range(n_snap):
        u = a * u + sig * rng.standard_normal(n)
        X[i] = u
    return X


def cov_spec(X):
    Y = X - X.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / (len(Y) - 1)


PS = [2.0, 2.5, 3.0]
eps = np.logspace(np.log10(0.9), np.log10(1e-9), 300)
rows, summary = [], {}
store = {}
for p in PS:
    X = ar1(p)
    lam = cov_spec(X)
    k = np.arange(1, len(lam) + 1)
    sel = (k >= 2) & (k <= 400)
    ps = np.polyfit(np.log(k[sel]), np.log(lam[sel]), 1)
    pfit = -ps[0]
    r = ranks(lam, eps)
    m = (r >= 5) & (r <= len(lam) * 0.10)
    sp = np.polyfit(np.log(1 / eps[m]), np.log(r[m]), 1)
    theo = 2 / (2 * pfit - 1)
    store[p] = dict(lam=lam, r=r, pfit=pfit, exp=float(sp[0]), theo=theo,
                    eps_exp=float(sp[0]), dev=(sp[0] - theo) / theo * 100)
    summary[f"lam_exp_{p}"] = dict(p_set=p, p_fit=float(pfit), eps_exp=float(sp[0]),
                                   theory=float(theo), dev_pct=float(store[p]["dev"]))
    for e, rr in zip(eps, r):
        rows.append([p, f"{e:.8g}", int(rr)])
    print(f"  λ~k^-{p}: p_fit={pfit:.3f}  理论指数={theo:.4f}  实测={sp[0]:.4f}  "
          f"偏差={store[p]['dev']:+.1f}%")

# ---- 写 txt ----
with io.open(os.path.join(FD, "figure5_algebraic_branch.txt"), "w", encoding="utf-8") as f:
    f.write("# Supplementary Figure 7: the algebraic branch, instantiated.\n")
    f.write("# System: near-neutral long-memory random field, u_k(t+1) = a u_k(t) + xi_k with\n")
    f.write("# a = 0.9999 and sigma_k = k^(-p/2) sqrt(1-a^2), so the stationary covariance is\n")
    f.write("# lambda_k = k^(-p). The relation predicts r(eps) ~ eps^(-2/(2p-1)) = eps^(-1/(p-1/2)).\n")
    f.write("# Columns: p_set, epsilon, rank_measured\n")
    f.write("p_set\tepsilon\trank_measured\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")
print(f"\n  已写 figure5_algebraic_branch.txt（{len(rows)} 行）")

# ---- 谱数据 ----
with io.open(os.path.join(FD, "figure5_algebraic_spectra.txt"), "w", encoding="utf-8") as f:
    f.write("# Supplementary Figure 7a: measured covariance spectra of the algebraic-branch systems.\n")
    f.write("# Columns: index_k, lambda_p2.0, lambda_p2.5, lambda_p3.0\n")
    f.write("index_k\tlambda_p2.0\tlambda_p2.5\tlambda_p3.0\n")
    for i in range(min(300, len(store[2.0]["lam"]))):
        f.write(f"{i+1}\t" + "\t".join(f"{store[p]['lam'][i]:.10g}" for p in PS) + "\n")
print(f"  已写 figure5_algebraic_spectra.txt")

json.dump(summary, io.open(os.path.join(AR, "v11_algebraic_branch.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
print("  已写 artifact v11_algebraic_branch.json")

# ---- 画图 ----
fig, ax = plt.subplots(1, 3, figsize=(13.2, 4.2))
for p in PS:
    s = store[p]
    k = np.arange(1, 301)
    ax[0].loglog(k, s["lam"][:300], lw=1.4, label=f"$\\lambda_k=k^{{-{p:.1f}}}$")
    ax[1].loglog(1 / eps, s["r"], lw=1.6, label=f"measured, $p$={s['pfit']:.2f}")
    ax[1].loglog(1 / eps, (1 / eps) ** s["theo"] * s["r"][len(eps)//2] * (1/eps[len(eps)//2]) ** (-s["theo"]),
                 "--", lw=1.0, alpha=.7)
ax[0].set_xlabel("mode index $k$"); ax[0].set_ylabel("covariance eigenvalue $\\lambda_k$")
ax[0].set_title("a  Prescribed algebraic spectra", fontsize=10); ax[0].legend(fontsize=8)
ax[1].set_xlabel("$1/\\epsilon$"); ax[1].set_ylabel("required rank $r(\\epsilon)$")
ax[1].set_title("b  Measured rank law (solid) vs theory (dashed)", fontsize=10)
ax[1].legend(fontsize=8)
devs = [store[p]["dev"] for p in PS]
ax[2].axhline(0, color="k", lw=.8)
ax[2].plot([f"{p:.1f}" for p in PS], devs, "o-", lw=1.4)
ax[2].set_xlabel("spectral exponent $p$"); ax[2].set_ylabel("deviation from theory (%)")
ax[2].set_title("c  Agreement with $2/(2p-1)$", fontsize=10)
ax[2].set_ylim(-15, 15)
for a_ in ax:
    a_.tick_params(labelsize=8)
plt.tight_layout()
out_png = os.path.join(FIGD, "FigS7_algebraic_branch.png")
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.close()
from PIL import Image
im = Image.open(out_png)
print(f"  已画 {out_png}  {im.size[0]}x{im.size[1]}")
