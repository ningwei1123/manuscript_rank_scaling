# -*- coding: utf-8 -*-
"""v6 figures: the corrected width experiments.

Fig6  Lorenz-96 width scan with reference curves and the measured power law
FigS3 Kuramoto-Sivashinsky width scans at two horizons
Also regenerates FigS2 as a historical record of the failed v3 scan.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image

load = lambda p: json.load(open(p, encoding="utf-8"))
S = load(os.path.join(ROOT, "width_law_v6_summary.json"))
L96 = S["lorenz96_width_law"]
KS5 = S["ks_width_scan_tau0p5"]
KS1 = S["ks_width_scan_tau0p125"]
OLD = load(os.path.join(ROOT, "real_l96_width.json"))

rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                 "mathtext.fontset": "stix", "font.size": 8.5, "axes.linewidth": 0.8,
                 "savefig.dpi": 300})
BLUE, ORANGE, GREEN, RED, PURPLE = "#1f4e79", "#c55a11", "#2e7d32", "#b3261e", "#6a1b9a"

def physical(png, target_in=5.70):
    im = Image.open(png); dpi = round(im.width / target_in); im.save(png, dpi=(dpi, dpi))

def interp_x(xs, ys, y0):
    """W at which the monotone-decreasing curve crosses y0 (log-x linear interp)."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    for i in range(len(xs) - 1):
        if ys[i] >= y0 >= ys[i + 1]:
            f = (y0 - ys[i]) / (ys[i + 1] - ys[i])
            return float(np.exp(np.log(xs[i]) + f * (np.log(xs[i + 1]) - np.log(xs[i]))))
    return None

# ===========================================================================
# FIG 6 -- corrected Lorenz-96 width scan
# ===========================================================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(5.70, 2.95))
W = np.array(L96["widths"], float)
M = np.array(L96["mse_mean"], float)
R = np.sqrt(M)
b = L96["baselines"]
r_triv, r_pers, r_ridge = np.sqrt(b["trivial"]), np.sqrt(b["persistence"]), np.sqrt(b["ridge_linear"])

a1.loglog(W, R, "o-", color=BLUE, ms=5, lw=1.5, label="MLP (Fourier trunk)")
a1.axhline(r_triv, color="k", ls="--", lw=1.1, label=f"trivial ({r_triv:.2f})")
a1.axhline(r_pers, color=ORANGE, ls="-.", lw=1.2, label=f"persistence ({r_pers:.2f})")
a1.axhline(r_ridge, color=GREEN, ls=":", lw=1.4, label=f"ridge linear ({r_ridge:.2f})")
mask = M < b["persistence"]
A = np.vstack([np.log(W[mask]), np.ones(mask.sum())]).T
c, *_ = np.linalg.lstsq(A, np.log(R[mask]), rcond=None)
a1.loglog(W[mask], np.exp(A @ c), "-", color=RED, lw=1.0, alpha=0.8,
          label=rf"fit: $E\sim W^{{-{L96['measured_gamma']:.2f}}}$ ($R^2={L96['measured_gamma_R2']:.2f}$)")
a1.set_xticks(W); a1.set_xticklabels([f"{int(w)}" for w in W])
a1.minorticks_off()
a1.set_xlabel("width $W$"); a1.set_ylabel(r"relative RMSE  $E(W)$")
a1.legend(fontsize=5.4, loc="lower left", framealpha=0.92,
          borderpad=0.3, labelspacing=0.26)
a1.grid(True, which="both", ls=":", lw=0.4, alpha=0.45)
a1.set_title("a  Lorenz-96: the width law is recovered", fontsize=8.5)

eps_grid = np.array([0.40, 0.35, 0.30, 0.25, 0.20, 0.15])
Wstar = [interp_x(W, R, e) for e in eps_grid]
ok = [w for w in Wstar if w is not None]
a2.plot([e for e, w in zip(eps_grid, Wstar) if w is not None], ok, "s-", color=BLUE, ms=6, lw=1.5)
for e, w in zip(eps_grid, Wstar):
    if w is not None:
        a2.annotate(f"{w:.0f}", (e, w), textcoords="offset points", xytext=(5, -3), fontsize=6.5)
a2.set_xlabel(r"target relative RMSE $\varepsilon$")
a2.set_ylabel(r"width required  $W^*(\varepsilon)$")
a2.set_xlim(0.13, 0.43)
a2.grid(True, ls=":", lw=0.4, alpha=0.45)
a2.set_title(r"b  Width vs accuracy (saturates near $W=256$)", fontsize=8.5)
a2.text(0.97, 0.05, f"$E\\sim W^{{-{L96['measured_gamma']:.2f}}}$\nover {mask.sum()} widths above persistence",
        transform=a2.transAxes, fontsize=6.2, ha="right", va="bottom",
        bbox=dict(fc="white", ec="0.75", lw=0.6))
fig.tight_layout(pad=0.5, w_pad=1.3)
p = os.path.join(FIGDIR, "Fig6_l96_width_v6.png")
fig.savefig(p, bbox_inches="tight"); plt.close(fig); physical(p)

# ===========================================================================
# FIG S3 -- KS width scans at two horizons
# ===========================================================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(5.70, 2.85))
for ax, D, lab in ((a1, KS1, r"$\tau=0.125$"), (a2, KS5, r"$\tau=0.5$")):
    w = np.array(D["widths"], float); r = np.sqrt(np.array(D["mse_mean"], float))
    bb = D.get("baselines_declared_in_script", D.get("baselines"))
    ax.loglog(w, r, "o-", color=BLUE, ms=5, lw=1.4, label="MLP")
    ax.axhline(np.sqrt(bb["persistence"]), color=ORANGE, ls="-.", lw=1.2,
               label=f"persistence ({np.sqrt(bb['persistence']):.3f})")
    if "fair_ridge_test_mse" in D:
        ax.axhline(np.sqrt(D["fair_ridge_test_mse"]), color=GREEN, ls=":", lw=1.3,
                   label=f"ridge, CV $\\lambda$ ({np.sqrt(D['fair_ridge_test_mse']):.2f})")
    else:
        ax.axhline(np.sqrt(bb["ridge_linear"]), color=GREEN, ls=":", lw=1.3,
                   label=f"ridge ({np.sqrt(bb['ridge_linear']):.2f})")
    ws = [k for k, v in D["W_star"].items() if v is not None]
    ax.set_xticks(w); ax.set_xticklabels([f"{int(x)}" for x in w])
    ax.minorticks_off()
    ax.set_xlabel("width $W$"); ax.set_ylabel(r"relative RMSE")
    ax.set_title(f"{lab}" + ("  (saturates)" if lab.endswith("0.5$") else ""), fontsize=8.5)
    ax.legend(fontsize=5.9, loc="upper right", framealpha=0.92)
    ax.grid(True, which="both", ls=":", lw=0.4, alpha=0.45)
a1.text(0.03, 0.05, "shorter horizon:\npersistence unbeatable", transform=a1.transAxes,
        fontsize=6.2, va="bottom", bbox=dict(fc="white", ec="0.75", lw=0.6))
a2.text(0.03, 0.05, "matches persistence,\nsaturates near $W\\approx64$", transform=a2.transAxes,
        fontsize=6.2, va="bottom", bbox=dict(fc="white", ec="0.75", lw=0.6))
fig.suptitle("Kuramoto-Sivashinsky width scans: no measurable width law at these horizons",
             fontsize=8.6, y=1.02)
fig.tight_layout(pad=0.5, w_pad=1.3)
p = os.path.join(FIGDIR, "FigS3_ks_width_v6.png")
fig.savefig(p, bbox_inches="tight"); plt.close(fig); physical(p)

print("FIGURES WRITTEN")
for fn in ("Fig6_l96_width_v6.png", "FigS3_ks_width_v6.png"):
    fp = os.path.join(FIGDIR, fn)
    print(f"  {fn:34s} {os.path.getsize(fp)/1024:8.1f} KB")
print(f"\nL96: gamma={L96['measured_gamma']:.4f} R2={L96['measured_gamma_R2']:.4f}; "
      f"beats persistence at {L96['beats_persistence_at_widths']}; ridge at {L96['beats_ridge_at_widths']}")
print(f"     W* per eps: " + ", ".join(f"{e}:{w if w is None else round(w)}" for e, w in zip(eps_grid, Wstar)))
print(f"KS tau=0.5: best rel.RMSE {np.min(np.sqrt(KS5['mse_mean'])):.4f} vs persistence "
      f"{np.sqrt(KS5['baselines_declared_in_script']['persistence']):.4f}")
