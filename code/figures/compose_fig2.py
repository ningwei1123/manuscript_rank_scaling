# -*- coding: utf-8 -*-
"""Compose Figure 2 as two panels: (a) the measured rank-accuracy curve,
(b) the window sensitivity of the fitted slope. M5 asked for (b) to be visible;
the text already cites Fig. 2b."""
import os
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

NUM = r"E:\nature投稿\探索1\数值验证"
FIGDIR = os.path.join(NUM, "figures")
rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                 "mathtext.fontset": "stix", "font.size": 8.5})

src = Image.open(os.path.join(FIGDIR, "Fig4_rank_law_test.png"))
w, h = src.size
fig = plt.figure(figsize=(5.70, 2.60))
axa = fig.add_axes([0.055, 0.06, 0.44, 0.86])
axa.imshow(src); axa.axis("off")
axa.text(0.0, 1.02, "a", transform=axa.transAxes, fontsize=10, fontweight="bold", va="bottom")

axb = fig.add_axes([0.585, 0.19, 0.39, 0.70])
cuts = np.arange(12, 32)
sl = []
A_KS = 0.711140115804443
from scipy.linalg import svd as csvd
f = np.load(os.path.join(NUM, "path2_ks_turb.npz"))["ksf"]
Xc = f - f.mean(axis=0, keepdims=True)
e = csvd(Xc, compute_uv=False) ** 2
tn = np.sqrt(np.maximum(1 - np.cumsum(e) / e.sum(), 0))
eg = np.logspace(-1, -5, 80)
r = np.array([min(int(np.searchsorted(-tn, -x)) + 1, len(e)) for x in eg], float)
for hi in cuts:
    m = (r > 0) & (r <= hi)
    sl.append(np.polyfit(np.log(1 / eg[m]), r[m], 1)[0] if m.sum() > 3 else np.nan)
axb.plot(cuts, sl, "o-", color="#1f4e79", ms=3.4, lw=1.3)
axb.axhline(1 / A_KS, color="#2e7d32", ls="--", lw=1.3)
axb.axhline(1 / (2 * A_KS), color="gray", ls=":", lw=1.2)
axb.set_ylim(0, 3.0)
axb.set_xlabel("upper rank cut-off", fontsize=7.6)
axb.set_ylabel("fitted slope", fontsize=7.6)
axb.tick_params(labelsize=7)
axb.grid(True, ls=":", lw=0.35, alpha=0.5)
axb.text(0.03, 0.05, rf"$1/\alpha$ = {1/A_KS:.2f}" + "\n" + rf"$1/(2\alpha)$ = {1/(2*A_KS):.2f}",
         transform=axb.transAxes, fontsize=6.4, va="bottom",
         bbox=dict(fc="white", ec="0.8", lw=0.5))
axb.text(0.0, 1.02, "b", transform=axb.transAxes, fontsize=10, fontweight="bold", va="bottom")

axc = fig.add_axes([0.10, 0.06, 0.82, 0.36]); axc.axis("off")
p = os.path.join(FIGDIR, "Fig2_measured_rank_law.png")
fig.savefig(p, dpi=300, facecolor="white")
plt.close(fig)
from PIL import Image as I
im = I.open(p); im.save(p, dpi=(round(im.width / 5.70),) * 2)
print(f"wrote {p}  {os.path.getsize(p)/1024:.1f} KB")
