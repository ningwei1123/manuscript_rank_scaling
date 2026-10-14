# -*- coding: utf-8 -*-
"""KS 定论：偏差对 (alpha 窗口 × 秩窗口) 的完整敏感性表。

这取代"一个 19% 的数字"，给出**偏差的真实范围**，并说明它为何发散。
"""
import io, json, os
import numpy as np

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
OUT = r"E:\deepseekworkspace\experiments_v12\v19_ks_sensitivity.json"


def load(fn):
    rows = []
    for line in io.open(os.path.join(FD, fn), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue
    return np.array(rows)


sp = load("figures1_ks_spectrum.txt")
ra = load("figure2_ks_rank_accuracy.txt")
k = sp[:, 0]; lam = sp[:, 1]
eps = ra[:, 0]; r = ra[:, 1]

# alpha 候选窗口
A_WINS = [(2, 32), (2, 22), (2, 14), (3, 20), (5, 20), (10, 20), (15, 25), (15, 32)]
# 秩窗口
R_WINS = [(0.3, 1e-4), (0.3, 1e-2), (0.1, 1e-4), (0.05, 1e-4), (0.3, 1e-3)]

print("=" * 112)
print("KS：alpha 窗口 × 秩窗口 的完整敏感性")
print("=" * 112)

alphas = {}
print("\n① 各窗口的 alpha（指数率）与 R²")
print(f"  {'窗口':>12}{'alpha':>11}{'R²':>10}{'beta(幂律)':>13}{'R²_pow':>10}")
for lo, hi in A_WINS:
    m = (k >= lo) & (k <= hi)
    if m.sum() < 5:
        continue
    lm = np.log(np.maximum(lam[m], 1e-300))
    s1 = np.polyfit(k[m], lm, 1)
    r2_1 = 1 - ((lm - np.polyval(s1, k[m])) ** 2).sum() / ((lm - lm.mean()) ** 2).sum()
    s2 = np.polyfit(np.log(k[m]), lm, 1)
    r2_2 = 1 - ((lm - np.polyval(s2, np.log(k[m]))) ** 2).sum() / ((lm - lm.mean()) ** 2).sum()
    alphas[(lo, hi)] = (-s1[0], r2_1, -s2[0], r2_2)
    print(f"  {f'{lo}-{hi}':>12}{-s1[0]:>11.6f}{r2_1:>10.4f}{-s2[0]:>13.6f}{r2_2:>10.4f}")

print()
print("② R = 秩斜率 × alpha（应 = 1）")
print(f"  {'alpha 窗口':>12}" + "".join(f"{f'r:{lo}..{hi}':>17}" for lo, hi in R_WINS))
rows = []
for aw, (a, r2a, b, r2b) in alphas.items():
    line = f"  {f'{aw[0]}-{aw[1]}':>12}"
    rec = dict(alpha_win=list(aw), alpha=a, r2_alpha=r2a)
    for lo, hi in R_WINS:
        mm = (eps <= lo) & (eps >= hi) & (r > 0)
        if mm.sum() < 5:
            line += f"{'--':>17}"
            continue
        sl = np.polyfit(np.log(1 / eps[mm]), r[mm], 1)[0]
        R = sl * a
        rec[f"R_{lo}_{hi}"] = float(R)
        rec[f"slope_{lo}_{hi}"] = float(sl)
        line += f"{R:>17.4f}"
    rows.append(rec)
    print(line)

print()
print("=" * 112)
print("③ 判读：偏差的真实范围")
print("=" * 112)
allR = []
for rec in rows:
    for kk, v in rec.items():
        if kk.startswith("R_"):
            allR.append(v)
allR = np.array(allR)
print(f"  R 的全部取值: {len(allR)} 个")
print(f"  范围: {allR.min():.4f} .. {allR.max():.4f}")
print(f"  中位: {np.median(allR):.4f}")
print(f"  距 1 的偏差范围: {abs(allR-1).min()*100:.1f}% .. {abs(allR-1).max()*100:.1f}%")
print(f"  中位偏差: {abs(np.median(allR)-1)*100:.1f}%")
print()
print(f"  含 R≈1 的配置数（|R-1|<0.1）: {int((abs(allR-1)<0.1).sum())}/{len(allR)}")
print()
print("  => 偏差随 alpha 窗口从 <5% 变到 >100%，即**不一致**。")
print("     统一口径下无法给出单一的偏差数字；这本身是结论：")
print("     KS 的谱不落在任一纯形式，故'一个 alpha'不存在，秩律在该系统上")
print("     只能给出**范围**而非点值。")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
