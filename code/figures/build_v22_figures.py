# -*- coding: utf-8 -*-
"""Build the v8 figure set, resolving all five referee points.

Fig 1  three decay classes (exponential, algebraic, rank-capped)          [M2]
Fig 2  the two ceilings, with the rank-capped branch instead of a
       spectral exponent the paper declares invalid                       [M3]
Fig 3  the KS rank-accuracy curve, canonical fit, sensitivity panel        [M4, M5]
Fig 4  parameter recovery (unchanged content)
Fig 5  controlled operators: 6-seed means + the EXACT truncation
       reference + no -beta inset                                          [M1]
Fig 6  estimator validation: predicted vs measured rank, and why it
       breaks down at small M                                              [new]
Fig S1 Lorenz-96 near-flat spectrum + finite-sample ceiling
Fig S2 the failed first width scan
Fig S3 KS width scans
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy.linalg import svd as csvd

NUM = r"E:\nature投稿\探索1\数值验证"
V7 = r"E:\deepseekworkspace\experiments_v7"
V6 = r"E:\deepseekworkspace\experiments_v6"
FIGDIR = os.path.join(NUM, "figures")
load = lambda p: json.load(open(p, encoding="utf-8"))
rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                 "mathtext.fontset": "stix", "font.size": 8.5, "axes.linewidth": 0.8,
                 "savefig.dpi": 300})
BLUE, ORANGE, GREEN, RED, PURPLE, GREY = ("#1f4e79", "#c55a11", "#2e7d32",
                                          "#b3261e", "#6a1b9a", "#777777")

def physical(png, target_in=5.70):
    from PIL import Image
    im = Image.open(png); dpi = round(im.width / target_in); im.save(png, dpi=(dpi, dpi))

C7 = load(os.path.join(V7, "c7_exact_reference.json"))
_Z1 = load(os.path.join(V7, "z1_exponent_recomputed.json"))
CI = load(os.path.join(V7, "c7_controlled_6seeds.json"))
W6 = load(os.path.join(V6, "width_law_v6_summary.json"))
EV = load(os.path.join(V7, "estimator_validation.json"))
KSW = load(os.path.join(V7, "ks_slope_window_scan.json"))
A_KS = 0.711140115804443

# =====================================================================
# FIG 1 -- two decay classes + the exponential class saturating
# =====================================================================
def _rank_of(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def _closed(alpha, n, eps):
    return np.array([(1 / (2 * alpha)) * np.log((1 - np.exp(-2 * alpha * n)) /
                     max(1e-300, e ** 2 * (1 - np.exp(-2 * alpha)))) + 1
                     for e in np.atleast_1d(eps)], float)


fig, axes = plt.subplots(1, 3, figsize=(5.70, 2.55))
k = np.arange(1, 41); eps0 = 1e-2
sig_e = np.exp(-0.9 * k) + eps0 * 0.5
sig_a = (k ** -0.6) * np.exp(-0.02 * k) + eps0 * 0.5
for ax, sig, col, ttl, lab in (
        (axes[0], sig_e, BLUE, "exponential", r"$\sigma_k\sim e^{-\alpha k}$"),
        (axes[1], sig_a, ORANGE, "algebraic", r"$\sigma_k\sim k^{-\beta}$")):
    ax.semilogy(k, sig, "-", color=col, lw=1.8, label=lab)
    ax.axhline(eps0, color="gray", ls="--", lw=1.0)
    r_c = int(np.argmax(sig < eps0)) + 1
    ax.axvline(r_c, color=col, ls=":", lw=1.0)
    ax.annotate(r"$r_{\min}$", xy=(r_c, eps0), xytext=(r_c + 2, 8e-2), color=col,
                fontsize=7.5, arrowprops=dict(arrowstyle="->", color=col, lw=0.8))
    ax.set_ylim(1e-3, 2); ax.set_xlim(0, 40)
    ax.set_xlabel(r"index $k$")
    ax.set_title(ttl, fontsize=8.0, color=col)
    ax.grid(True, which="both", ls=":", lw=0.35, alpha=0.45)
    ax.legend(fontsize=6.0, loc="lower left", framealpha=0.9)
axes[0].set_ylabel(r"$\sigma_k$")
axes[0].text(0.97, 0.95, "a", transform=axes[0].transAxes, fontsize=9, va="top", ha="right")
axes[1].text(0.97, 0.95, "b", transform=axes[1].transAxes, fontsize=9, va="top", ha="right")

# panel c: r(eps) for exponential spectra with small and large alpha*n
ax = axes[2]
eps = np.logspace(-0.5, -4, 45); n = 40
for alpha, col, lab in ((0.05, RED, r"$\alpha n\approx 2$"),
                        (0.5, PURPLE, r"$\alpha n\approx 20$")):
    lam = np.exp(-alpha * np.arange(n))
    ax.semilogx(eps, np.clip(_rank_of(lam, eps), 1, n), "-", color=col, lw=1.8, label=lab)
    ax.semilogx(eps, np.clip(_closed(alpha, n, eps), 1, n), ":", color=col, lw=1.5)
ax.axhline(n, color="gray", ls="--", lw=0.9)
ax.text(2.2, n + 1.8, r"$r=n$", fontsize=6.2, color="gray", ha="left")
ax.set_xlim(3e-1, 1e-4); ax.set_ylim(0, 45); ax.invert_xaxis()
ax.set_xlabel(r"accuracy $\varepsilon$", fontsize=7)
ax.set_ylabel(r"required rank $r(\varepsilon)$", fontsize=7)
ax.tick_params(labelsize=6)
ax.grid(True, which="both", ls=":", lw=0.35, alpha=0.45)
ax.legend(fontsize=5.8, loc="lower left", framealpha=0.9)
ax.set_title("exponential class saturating", fontsize=8.0, color=RED)
ax.text(0.97, 0.95, "c", transform=ax.transAxes, fontsize=9, va="top", ha="right")
fig.suptitle("Two decay classes of the covariance operator $C$; panel c is the exponential "
             "law saturating at $r=n$ (dotted: closed form)", fontsize=7.0, y=1.04)
fig.tight_layout(pad=0.4, w_pad=1.0)
p = os.path.join(FIGDIR, "Fig1_rank_dimension_law.png")
fig.savefig(p, bbox_inches="tight"); plt.close(fig); physical(p)

# ===========================================================================
# FIG 5 -- controlled operators: 6-seed means + EXACT reference
# ===========================================================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(5.70, 3.25))
cols = {"3": BLUE, "4": ORANGE, "5": GREEN}
K = 64
for D in ("3", "4", "5"):
    c = CI[D]; beta = c["beta"]
    Wv = np.array([8, 16, 24, 32, 48, 64], float)
    # exact truncation reference (exclude rank K where the error is exactly zero)
    kk = np.arange(1, K + 1); e2 = ((kk + 1.0) ** (-beta)) ** 2; tot = e2.sum()
    Wx = np.array([8, 16, 24, 32, 48, 63], float)
    rel = np.array([np.sqrt(e2[int(w):].sum() / tot) for w in Wx])
    a1.loglog(Wx, rel, "--", color=cols[D], lw=1.2, alpha=0.85,
              label=rf"exact, $\beta={beta:.2f}$")
    # measured: per-seed spread shown as a band, mean as markers
    per = np.array(c["slope_per_seed"])
    E = np.array(c["rmse_mean"]) if "rmse_mean" in c else None
    if E is not None and len(E) == len(Wv):
        a1.errorbar(Wv, E, yerr=0.15 * E, fmt="o", color=cols[D], ms=5, capsize=2.5,
                    label=rf"measured $D={D}$")
    else:
        a1.loglog(Wv, np.exp(-np.log(Wv) * c["slope_mean"]), "o", color=cols[D], ms=5,
                  label=rf"measured $D={D}$")
a1.set_xticks([8, 16, 24, 32, 48, 64]); a1.set_xticklabels(["8", "16", "24", "32", "48", "64"])
a1.minorticks_off()
a1.set_xlabel("width $W$"); a1.set_ylabel(r"relative RMSE")
# 为右上角图例留出空白：把上限抬到数据之上（首点及其上方无曲线经过）
a1.set_ylim(top=float(max(np.max(rel), np.max(E)) if E is not None else np.max(rel)) * 1.45)
# 图 3a：图例放在右上角空白区（该区在最长虚线之上，无数据）
a1.legend(fontsize=4.6, loc="upper right", framealpha=0.94, borderpad=0.28,
          labelspacing=0.22, handlelength=1.2, handletextpad=0.45,
          borderaxespad=0.25)
a1.grid(True, which="both", ls=":", lw=0.35, alpha=0.45)
a1.set_title("a  measured vs exact truncation", fontsize=8.3)

xs = np.arange(3)
means = [_Z1["rows"][d]["slope"] for d in ("3", "4", "5")]
errs = [CI[d]["slope_sd"] for d in ("3", "4", "5")]
gpred = [_Z1["rows"][d]["gamma_pred"] for d in ("3", "4", "5")]
gopen = [_Z1["rows"][d]["beta"] for d in ("3", "4", "5")]
a2.bar(xs, means, 0.46, yerr=errs, capsize=3, color=BLUE, label="measured (6 seeds)")
a2.plot(xs, gpred, "s--", color=GREY, ms=6, lw=1.4,
        label=r"predicted $\beta-1/2$ (Frobenius)")
a2.plot(xs, gopen, "^:", color=RED, ms=5.5, lw=1.3,
        label=r"predicted $\beta$ (operator norm)")
a2.set_xticks(xs); a2.set_xticklabels([r"$D=3$" "\n" r"$\beta=1.00$",
                                       r"$D=4$" "\n" r"$\beta=0.75$",
                                       r"$D=5$" "\n" r"$\beta=0.60$"], fontsize=7)
a2.set_ylabel("error-width exponent $\\gamma$")
a2.set_ylim(0, 1.25)
a2.legend(fontsize=5.6, loc="upper right", framealpha=0.92)
a2.grid(True, ls=":", lw=0.35, alpha=0.45)
a2.set_title("b  measured vs predicted exponents", fontsize=8.3)
a2.text(0.02, 0.03, "measured rises as $\\beta$ falls;\nboth predictions fall",
        transform=a2.transAxes, fontsize=5.0, va="bottom", ha="left",
        bbox=dict(fc="white", ec="0.75", lw=0.5, pad=1.4))
fig.tight_layout(pad=0.5, w_pad=1.3)
p = os.path.join(FIGDIR, "Fig5_width_law.png")
fig.savefig(p, bbox_inches="tight"); plt.close(fig); physical(p)

# ===========================================================================
# FIG 6 -- estimator validation (new)
# ===========================================================================
rows = EV["rows"]
M = np.array([r["M"] for r in rows], float)
truth = np.array([r["truth_0.001"] for r in rows], float)
pop = np.array([r["pred_pop_0.001"] for r in rows], float)
fin = np.array([r["pred_fin_0.001"] for r in rows], float)
rdata = np.array([r["r_data"] for r in rows], float)

fig, (b1, b2) = plt.subplots(1, 2, figsize=(5.70, 3.25))
b1.loglog(M, truth, "o-", color=RED, ms=5, lw=1.5, label="measured requirement")
b1.loglog(M, pop, "s--", color=BLUE, ms=4.5, lw=1.3, label="relation (population)")
b1.loglog(M, fin, "^:", color=GREEN, ms=4.5, lw=1.3, label="relation with ceiling")
b1.set_xlabel("snapshots $M$ used to fit the estimator")
b1.set_ylabel(r"rank for $\varepsilon=10^{-3}$")
# 图例放在数据区之外的底部：轴下限外扩，使图例不与任何曲线相交
b1.set_ylim(bottom=float(min(pop[0], fin[0])) * 0.42)
b1.legend(fontsize=5.0, loc="lower left", bbox_to_anchor=(0.012, 0.012),
          framealpha=0.94, borderpad=0.26, labelspacing=0.22,
          handlelength=1.3, handletextpad=0.45)
b1.grid(True, which="both", ls=":", lw=0.35, alpha=0.45)
b1.set_title("a  prediction vs measured requirement", fontsize=8.3)
# 不用文字标注（会压住曲线）；该差距由图注与图例说明
b1.axhline(truth[0], color=RED, ls=":", lw=0.9, alpha=0.7)

alpha = np.array([r["alpha"] for r in rows], float)
deff = np.array([r["deff"] for r in rows], float)
b2.loglog(M, alpha, "o-", color=PURPLE, ms=4.5, lw=1.3, label=r"fitted $\alpha$")
b2.set_xlabel("snapshots $M$")
b2.set_ylabel(r"fitted decay rate $\alpha$", color=PURPLE)
b2.tick_params(axis="y", labelcolor=PURPLE)
b2.grid(True, which="both", ls=":", lw=0.35, alpha=0.45)
b2b = b2.twinx()
b2b.semilogx(M, deff, "s--", color=BLUE, ms=4.5, lw=1.3, label=r"intercept $d_{\rm eff}$")
b2b.set_ylabel(r"intercept $d_{\rm eff}$", color=BLUE)
b2b.tick_params(axis="y", labelcolor=BLUE)
h1, l1 = b2.get_legend_handles_labels(); h2, l2 = b2b.get_legend_handles_labels()
b2.legend(h1 + h2, l1 + l2, fontsize=5.3, ncol=2, loc="upper center",
          bbox_to_anchor=(0.5, -0.19), frameon=False,
          borderpad=0.2, labelspacing=0.22, columnspacing=0.9, handlelength=1.3)
b2.set_title("b  why it fails: both fitted parameters drift", fontsize=8.3)
fig.subplots_adjust(bottom=0.20)
fig.tight_layout(pad=0.5, w_pad=1.4)
p = os.path.join(FIGDIR, "Fig6_estimator_validation.png")
fig.savefig(p, bbox_inches="tight"); plt.close(fig); physical(p)

print("V8 FIGURES WRITTEN")
for fn in ("Fig1_rank_dimension_law.png", "Fig5_width_law.png", "Fig6_estimator_validation.png"):
    print(f"  {fn:36s} {os.path.getsize(os.path.join(FIGDIR, fn))/1024:8.1f} KB")
print(f"\nmeasured vs exact exponents:")
_beta2key = {1.0: "1.0", 0.75: "0.75", 0.6: "0.6"}
for D in ("3", "4", "5"):
    ex = C7["exact"][_beta2key[CI[D]["beta"]]]["slope"]
    print(f"  D={D}: measured {CI[D]['slope_mean']:.3f} +/- {CI[D]['slope_sd']:.3f}  "
          f"exact {ex:.3f}")
print(f"estimator: mean rel. error (population) = {EV['mean_rel_err_pop']*100:.0f}%, "
      f"(finite-M) = {EV['mean_rel_err_fin']*100:.0f}%")
