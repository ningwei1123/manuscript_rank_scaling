# -*- coding: utf-8 -*-
"""v22：重画图 1 的 panel c —— 从「第三类」改为「指数类的饱和」。

新 panel c 展示指数律在 αn 小时的饱和：
  · 两条精确指数谱（αn ≈ 2 与 αn ≈ 20）
  · 各自的实测 r(ε) 与 Eq.(3) 闭式预测（虚线）
  · 直观显示 αn 小时 r 迅速到达 n 上界（看似"封顶"）
"""
import os as _os
REPO = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
ART = _os.path.join(REPO, "data", "artifacts")
FIGDIR = _os.path.join(REPO, "figures")
FDATA = _os.path.join(REPO, "data", "figure_data")
import io, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

if not os.path.isdir(FIGDIR):
    for cand in (r"" + ART + os.sep + "figures",
                 r"E:\deepseekworkspace\ncs_v6"):
        if os.path.isdir(cand):
            FIGDIR = cand; break
OUT = os.path.join(FIGDIR, "Fig1_panel_c_new.png")
BLUE, ORANGE = "#1f4e79", "#c55a11"


def rank_of(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def closed_form(alpha, n, eps):
    return np.array([(1 / (2 * alpha)) * np.log((1 - np.exp(-2 * alpha * n)) /
                     max(1e-300, e ** 2 * (1 - np.exp(-2 * alpha)))) + 1
                     for e in np.atleast_1d(eps)], float)


fig, ax = plt.subplots(figsize=(2.05, 2.35))
eps = np.logspace(-1, -6, 40)
n = 40
for alpha, col, lab in ((0.05, ORANGE, r"$\alpha n \approx 2$"),
                        (0.5, BLUE, r"$\alpha n \approx 20$")):
    lam = np.exp(-alpha * np.arange(n))
    r_meas = np.clip(rank_of(lam, eps), 1, n)
    r_pred = np.clip(closed_form(alpha, n, eps), 1, n)
    ax.semilogx(eps, r_meas, "-", color=col, lw=1.8, label=lab)
    ax.semilogx(eps, r_pred, ":", color=col, lw=1.4, dashes=(3, 2))
    ax.axhline(n, color="gray", ls="--", lw=0.9)
ax.text(3e-6, n + 1.6, r"$r=n$", fontsize=6.2, color="gray", ha="left")
ax.text(2e-2, 33, r"closed form (Eq. 3)", fontsize=5.4, color="k", ha="left")
ax.set_xlim(1e-1, 1e-6); ax.set_ylim(0, 45)
ax.invert_xaxis()
ax.set_xlabel(r"accuracy $\varepsilon$", fontsize=7)
ax.set_ylabel(r"required rank $r(\varepsilon)$", fontsize=7)
ax.tick_params(labelsize=6)
ax.grid(True, which="both", ls=":", lw=0.35, alpha=0.45)
ax.legend(fontsize=5.8, loc="upper left", framealpha=0.9)
ax.set_title("saturation of the exponential class", fontsize=7.2, color=ORANGE)
ax.text(0.97, 0.95, "c", transform=ax.transAxes, fontsize=9, va="top", ha="right")
fig.tight_layout(pad=0.35)
fig.savefig(OUT, bbox_inches="tight", dpi=400)
plt.close(fig)
print("wrote", OUT)
