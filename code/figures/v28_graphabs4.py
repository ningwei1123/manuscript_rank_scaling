# -*- coding: utf-8 -*-
"""图形摘要 v4：用实测宽度约束布局，确保不溢出。

方法：先测量候选文字在该字号下的实际像素宽度，选出能放进对应格子的字号；
      不依赖猜测。
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image

OUT = r"E:\deepseekworkspace\JCP_submission\Graphical_abstract.png"
BLUE, ORANGE, RED, GREY, GREEN = "#1f4e79", "#c55a11", "#b3261e", "#6b6b6b", "#2e7d32"
plt.rcParams.update({"font.family": "sans-serif",
                     "font.sans-serif": ["Arial", "DejaVu Sans"]})
W, H, DPI = 1328, 531, 300


def widest(texts, fs):
    """返回给定字号下这些文本的最大像素宽度。"""
    f = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    r = f.canvas.get_renderer()
    m = 0.0
    for t in texts:
        o = f.text(0.5, 0.5, t, fontsize=fs)
        m = max(m, o.get_window_extent(r).width)
        o.remove()
    plt.close(f)
    return m


def fit_fs(texts, target_px, hi=16.0, lo=4.0):
    """二分找最大字号，使最宽文本 ≤ target_px。"""
    for _ in range(24):
        mid = (hi + lo) / 2
        if widest(texts, mid) <= target_px:
            lo = mid
        else:
            hi = mid
    return lo


TITLE = "A spectral diagnostic for model-size scaling laws in chaotic systems"
fs_title = fit_fs([TITLE], 1180)
print(f"标题字号 -> {fs_title:.2f} pt（宽度 {widest([TITLE], fs_title):.0f} px）")

BODIES = [
    ["Model size is taken from", "the covariance spectrum, but", "no criterion says when", "that choice is sound"],
    ["The Koopman operator of a", "measure-preserving system is", "unitary: it carries no", "decaying spectrum"],
    ["exponential spectrum:", "r ~ (1/a) ln(1/e)", "algebraic spectrum:", "r ~ e^(-1/(b-1/2))"],
    ["16 of 18 synthetic systems", "classified correctly, but only", "1 of 8 real SST fields, where", "the class itself flips"],
]
PW = 0.234                       # figure 分数（收窄以留边距）
PW_px = PW * W - 24              # 留 24 px 内边距
fs_body = min(fit_fs(b, PW_px) for b in BODIES)
print(f"面板正文字号 -> {fs_body:.2f} pt（各面板最大宽度 "
      f"{[round(widest(b, fs_body)) for b in BODIES]} px，可用 {PW_px:.0f} px）")

CONC = ["Only two spectral classes are needed. The third apparent",
        "class is the exponential law saturating at the state dimension."]
PRAC = ["Practical reading: trust a spectral estimate of model size",
        "only when the spectral span is large and the convention is",
        "fixed before the class is read off."]
AVAIL = 0.955 * W - 0.350 * W
fs_concl = min(fit_fs(CONC, AVAIL), fit_fs(PRAC, AVAIL))
print(f"结论文字字号 -> {fs_concl:.2f} pt（最大宽度 "
      f"{max(widest(CONC, fs_concl), widest(PRAC, fs_concl)):.0f} px，可用 {AVAIL:.0f} px）")

# ---------------- 绘制 ----------------
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
ov = fig.add_axes([0, 0, 1, 1]); ov.axis("off"); ov.set_xlim(0, 1); ov.set_ylim(0, 1)
fig.text(0.5, 0.972, TITLE, ha="center", va="top", fontsize=fs_title,
         fontweight="bold", color="#141414")

PANELS = [(0.026, BLUE, "PROBLEM"), (0.256, ORANGE, "WHY THE USUAL GUIDE FAILS"),
          (0.486, GREEN, "CLOSED FORM GIVEN"), (0.716, RED, "BOUNDARY OF VALIDITY")]
PY, PH = 0.500, 0.390
for (x, col, title), body in zip(PANELS, BODIES):
    ov.add_patch(FancyBboxPatch((x, PY), PW, PH, boxstyle="round,pad=0.004,rounding_size=0.012",
                                fc=col, ec=col, lw=1.3, alpha=0.09, zorder=1))
    ov.add_patch(FancyBboxPatch((x, PY), PW, PH, boxstyle="round,pad=0.004,rounding_size=0.012",
                                fc="none", ec=col, lw=1.3, zorder=2))
    fig.text(x + PW / 2, PY + PH - 0.028, title, ha="center", va="top", fontsize=fs_body,
             color=col, fontweight="bold")
    fig.text(x + PW / 2, PY + PH - 0.098, "\n".join(body), ha="center", va="top",
             fontsize=fs_body, linespacing=1.6, color="#1a1a1a")
for k in range(3):
    x0 = PANELS[k][0] + PW
    ov.add_patch(FancyArrowPatch((x0 + 0.002, PY + PH / 2), (x0 + 0.016, PY + PH / 2),
                                 arrowstyle="-|>", mutation_scale=10, lw=1.3, color=GREY, zorder=6))

axb = fig.add_axes([0.032, 0.100, 0.280, 0.320])
eps = np.logspace(-1, -6, 60); n = 40
for alpha, col, lab in ((0.05, RED, "saturating"), (0.5, BLUE, "logarithmic")):
    lam = np.exp(-alpha * np.arange(n)); e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    axb.semilogx(eps, np.clip([int(np.searchsorted(-rel, -e)) + 1 for e in eps], 1, n),
                 "-", color=col, lw=1.4, label=lab)
axb.axhline(n, color=GREY, ls="--", lw=0.8)
axb.set_xlim(1e-1, 1e-6); axb.set_ylim(0, 45); axb.invert_xaxis()
axb.tick_params(labelsize=5.4)
axb.set_xlabel(r"accuracy $\varepsilon$", fontsize=6.0, labelpad=1)
axb.set_ylabel("required rank", fontsize=6.0, labelpad=1)
axb.grid(True, which="both", ls=":", lw=0.28, alpha=0.45)
axb.legend(fontsize=5.2, loc="upper left", framealpha=0.9, handlelength=1.3)
axb.set_title("two classes, not three", fontsize=6.4, pad=2)

fig.text(0.345, 0.360, "\n".join(CONC), ha="left", va="top", fontsize=fs_concl,
         linespacing=1.5, color="#1a1a1a")
fig.text(0.345, 0.240, "\n".join(PRAC), ha="left", va="top", fontsize=fs_concl,
         linespacing=1.5, color=RED)

fig.savefig(OUT, dpi=DPI); plt.close(fig)

# 复核：非白像素不得触及边界
im = Image.open(OUT).convert("L")
a = np.array(im); ys, xs = np.where(a < 240)
print(f"\nwrote {OUT}")
print(f"  尺寸 {Image.open(OUT).size}   dpi {Image.open(OUT).info.get('dpi',(0,0))[0]:.0f}  "
      f"体积 {os.path.getsize(OUT)/1024:.0f} KB")
print(f"  内容范围 x∈[{xs.min()},{xs.max()}] y∈[{ys.min()},{ys.max()}]  （画布 0..{W-1}, 0..{H-1}）")
edge = (xs.min() <= 1) or (xs.max() >= W - 2) or (ys.min() <= 1) or (ys.max() >= H - 2)
print(f"  是否触及边界: {'是（可能被裁切）' if edge else '否  OK'}")
