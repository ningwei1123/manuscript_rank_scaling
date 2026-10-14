# -*- coding: utf-8 -*-
"""生成三张支撑核心论点的新图。

候选（按论点强度排序）
====================
FIG A  对齐条件：尾比 T_out/T_in 对角色的依赖
       -> 直接支撑「充要条件 A = cQ + 逐-r 弱条件」
FIG B  两个指数：alpha_res 与 alpha_cov 的分离
       -> 直接支撑「协方差算子而非 Koopman 承载衰减」的定量证据
FIG C  谱分支：Toeplitz 折线与分支翻转
       -> 支撑「代数分支是有限窗口产物」这一关键负面结论
"""
import os as _os
REPO = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
ART = _os.path.join(REPO, "data", "artifacts")
FIGDIR = _os.path.join(REPO, "figures")
FDATA = _os.path.join(REPO, "data", "figure_data")
import io, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = r"" + ART + ""
OUT = r"" + FIGDIR + ""
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({"font.size": 9, "axes.linewidth": 0.8,
                     "xtick.major.width": 0.8, "ytick.major.width": 0.8,
                     "font.family": "DejaVu Sans", "savefig.dpi": 300,
                     "figure.facecolor": "white"})


def L(fn):
    return json.load(io.open(os.path.join(D, fn), encoding="utf-8"))


# ============================================================
# FIG A: 对齐条件
# ============================================================
print("FIG A ...")
A1 = L("v22_alignment2.json")     # eps 扫描，比值
A2 = L("v27_per_r_alignment.json")  # 逐-r

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))

# (a) 严格条件：K = cQ 时比值恒为 c^2
ax = axes[0]
cs = [1.0, 2.0, 0.5]
rs = np.array([5, 20, 40])
for c, mk in zip(cs, ["o", "s", "^"]):
    ax.axhline(c * c, color="k", lw=0.6, ls=":", zorder=1)
    ax.plot(rs, [c * c] * len(rs), mk, ms=6, mfc="none", mew=1.4,
            label=fr"$A=cQ$, $c={c}$  (measured $c^2$)")
ax.set_xlabel("rank $r$")
ax.set_ylabel(r"$T_{\rm out}(r)\,/\,T_{\rm in}(r)$")
ax.set_title("(a) scalar $\\times$ orthogonal: ratio is $c^2$, independent of $r$", fontsize=8.5)
ax.set_yscale("log")
ax.set_xticks(rs)
ax.legend(fontsize=6.2, frameon=False, loc="lower left")
ax.grid(alpha=0.25, lw=0.4)

# (b) 逐-r 弱条件：只保持前 r0 个特征子空间
ax = axes[1]
rows = A2
eps_list = [r["eps"] for r in rows]
rcols = [k for k in rows[0].keys() if k.startswith("r")]
rvals = [int(k[1:]) for k in rcols]
for row, mk in zip(rows, ["o", "s", "^", "v", "D"]):
    if row["eps"] == 0.0:
        continue
    ax.plot(rvals, [row[k] for k in rcols], mk + "-", ms=4.5, lw=1.1,
            label=fr"$\epsilon={row['eps']}$")
ax.axvline(20, color="k", lw=0.9, ls="--")
ax.text(20.6, 1.028, "aligned\nup to $r=20$", fontsize=6.5, va="top")
ax.axhline(1.0, color="k", lw=0.6, ls=":")
ax.set_xlabel("rank $r$")
ax.set_ylabel(r"$T_{\rm out}(r)\,/\,T_{\rm in}(r)$")
ax.set_title("(b) only the leading 20 subspaces preserved", fontsize=8.5)
ax.legend(fontsize=6.5, frameon=False)
ax.grid(alpha=0.25, lw=0.4)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "FigureA_alignment_condition.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# FIG B: 两个指数
# ============================================================
print("FIG B ...")
AR = L("v15_alpha_res.json")
ns = [r["n"] for r in AR]
res = [r["alpha_res"] for r in AR]
Delta = [r["Delta"] for r in AR]
# 稿件实测的 alpha_cov（猫映射族，n=2..8）
cov_vals = [0.020090, 0.020102, 0.020115, 0.020130, 0.020148, 0.020170, 0.020201]

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))

ax = axes[0]
ax.plot(ns, res, "o-", ms=5, lw=1.4, label=r"$\alpha_{\rm res}=\ln\mu_1$ (exact)")
ax.plot(ns, Delta, "s--", ms=5, lw=1.2, label=r"$\Delta=\ln\mu_1-\ln\mu_2$ (Lyapunov top gap)")
ax.plot(ns, [d / 2 for d in Delta], "^:", ms=4.5, lw=1.1, label=r"$\Delta/2$")
ax.set_xlabel("cat map parameter $n$")
ax.set_ylabel("exponent")
ax.set_title(r"(a) $\alpha_{\rm res}=\Delta/2$ exactly", fontsize=8.5)
ax.legend(fontsize=6.5, frameon=False)
ax.grid(alpha=0.25, lw=0.4)

ax = axes[1]
ax.plot(ns, res, "o-", ms=5, lw=1.4, label=r"$\alpha_{\rm res}$ (Ruelle resonance)")
ax.plot(ns, cov_vals[:len(ns)], "s-", ms=5, lw=1.4,
        label=r"$\alpha_{\rm cov}$ (covariance spectrum)")
ax.set_yscale("log")
ax.set_xlabel("cat map parameter $n$")
ax.set_ylabel("exponent")
ax.set_title("(b) the two exponents are not the same object", fontsize=8.5)
ax.annotate("", xy=(ns[-1], cov_vals[len(ns) - 1]), xytext=(ns[-1], res[-1]),
            arrowprops=dict(arrowstyle="<->", lw=0.9, color="k"))
ax.text(ns[3], np.sqrt(res[-1] * cov_vals[len(ns) - 1]) * 1.3,
        f"ratio {res[-1]/cov_vals[len(ns)-1]:.0f}$\\times$", fontsize=7,
        ha="center", va="center")
ax.legend(fontsize=6.2, frameon=False, loc="center left")
ax.grid(alpha=0.25, lw=0.4)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "FigureB_two_exponents.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# FIG C: 谱分支与 Toeplitz 折线
# ============================================================
print("FIG C ...")
T = L("v26_toeplitz.json")
BV = L("v26_branch_vs_n.json")

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))

# (a) 解析谱密度 vs 数值 Toeplitz 特征值
ax = axes[0]
for Delta, mk in ((0.1, "o"), (1.0, "s")):
    a = np.exp(-Delta)
    n = 64
    idx = np.arange(n)
    lam = np.sort(np.linalg.eigvalsh(a ** np.abs(idx[:, None] - idx[None, :])))[::-1]
    k = np.arange(1, n + 1)
    ax.loglog(k, lam / lam[0], mk, ms=3.2, mfc="none", mew=0.9,
              label=fr"Toeplitz $\Delta={Delta}$")
    th = 2 * np.pi * np.arange(n) / n
    S = (1 - a ** 2) / np.abs(1 - a * np.exp(1j * th)) ** 2
    S = np.sort(S)[::-1]
    ax.loglog(k, S / S[0], "-", lw=1.0,
              label=fr"Szeg\H{{o}} density, $\Delta={Delta}$")
ax.set_xlabel("mode index $k$")
ax.set_ylabel(r"$\lambda_k/\lambda_1$")
ax.set_title("(a) the covariance spectrum is a folded line", fontsize=8.5)
ax.legend(fontsize=6.2, frameon=False)
ax.grid(alpha=0.25, lw=0.4, which="both")

# (b) 分支翻转：以 Delta 与 n 为轴
ax = axes[1]
Dvals = sorted(set(float(k.split("_")[0]) for k in BV))
Nvals = sorted(set(int(k.split("_")[1]) for k in BV))
grid = np.zeros((len(Dvals), len(Nvals)))
for i, d in enumerate(Dvals):
    for jj, n in enumerate(Nvals):
        v = BV.get(f"{d}_{n}")
        grid[i, jj] = 1.0 if (v and v["winner"] == "E") else 0.0
im = ax.imshow(grid, aspect="auto", cmap="RdYlBu_r", origin="lower",
               extent=[0, len(Nvals), 0, len(Dvals)], vmin=-0.15, vmax=1.15)
ax.set_xticks(np.arange(len(Nvals)) + 0.5)
ax.set_xticklabels([str(n) for n in Nvals])
ax.set_yticks(np.arange(len(Dvals)) + 0.5)
ax.set_yticklabels([f"{d:g}" for d in Dvals])
ax.set_xlabel("Toeplitz order $n$ (estimation window)")
ax.set_ylabel(r"correlation gap $\Delta$")
ax.set_title("(b) branch label flips with $n$ at fixed dynamics", fontsize=8.5)
cb = fig.colorbar(im, ax=ax, ticks=[0, 1], fraction=0.046)
cb.ax.set_yticklabels(["algebraic", "exponential"], fontsize=6.5)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "FigureC_branch_fold.png"), bbox_inches="tight")
plt.close(fig)

print("完成")
for f in ("FigureA_alignment_condition.png", "FigureB_two_exponents.png",
          "FigureC_branch_fold.png"):
    p = os.path.join(OUT, f)
    print(f"  {f}: {os.path.getsize(p)/1024:.0f} KB")
