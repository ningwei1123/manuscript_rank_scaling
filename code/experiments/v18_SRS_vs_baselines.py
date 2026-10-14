# -*- coding: utf-8 -*-
"""第 1 项定稿（修正指标）：用「达标率」与「绝对误差」替代爆表的相对比。"""
import io, json
import numpy as np

SRC = r"E:\deepseekworkspace\experiments_v12\v18_srs_final.json"
OUT = r"E:\deepseekworkspace\experiments_v12\v18_srs_metrics.json"
j = json.load(io.open(SRC, encoding="utf-8"))
rows = j["rows"]

print(f"共 {len(rows)} 组\n")

# 目标误差：取 CV 的结果作为「黄金标准」
tgt = np.array([r["b4"] for r in rows])
best = np.array([min(r["srs"], r["b1"], r["b2"], r["b3"], r["b4"]) for r in rows])

print("=" * 118)
print("指标 1：绝对误差（中位 / 90 分位）")
print("=" * 118)
print(f"  {'方法':<8}{'秩中位':>8}{'误差中位':>13}{'误差90分位':>14}{'训练次数':>10}")
summ = {}
for meth, kr, ke, nc in (("SRS", "r_srs", "srs", 1), ("E99", "r_b1", "b1", 1),
                         ("Scree", "r_b2", "b2", 1), ("Fixed", "r_b3", "b3", 1),
                         ("CV", "r_b4", "b4", 20)):
    es = np.array([r[ke] for r in rows]); rs = np.array([r[kr] for r in rows])
    summ[meth] = dict(rank_med=float(np.median(rs)),
                      err_med=float(np.median(es)),
                      err_p90=float(np.percentile(es, 90)), ncalls=int(nc))
    print(f"  {meth:<8}{np.median(rs):>8.1f}{np.median(es):>13.3e}"
          f"{np.percentile(es,90):>14.3e}{nc:>10}")

print()
print("=" * 118)
print("指标 2：达标率（误差 <= k × 黄金标准 CV 的比例）")
print("=" * 118)
print(f"  {'方法':<8}" + "".join(f"{'k='+str(k):>10}" for k in (1.0, 2.0, 5.0, 10.0, 100.0))
      + f"{'训练次数':>10}")
hit = {}
for meth, ke, nc in (("SRS", "srs", 1), ("E99", "b1", 1), ("Scree", "b2", 1),
                     ("Fixed", "b3", 1), ("CV", "b4", 20)):
    es = np.array([r[ke] for r in rows])
    hs = []
    for k in (1.0, 2.0, 5.0, 10.0, 100.0):
        # CV 本身是最优，允许 1% 容差
        hs.append(float((es <= (k + 1e-9) * np.maximum(tgt, 1e-12)).mean() * 100))
    hit[meth] = dict(zip([f"k{k}" for k in (1.0, 2.0, 5.0, 10.0, 100.0)], hs))
    print(f"  {meth:<8}" + "".join(f"{h:>9.0f}%" for h in hs) + f"{nc:>10}")

print()
print("=" * 118)
print("指标 3：计算节省 × 精度代价")
print("=" * 118)
cv_calls = 20
print(f"  CV（黄金标准）: 训练 {cv_calls} 次，达标率 100%（定义）")
for meth in ("SRS", "E99", "Scree", "Fixed"):
    h10 = hit[meth]["k10.0"]
    h100 = hit[meth]["k100.0"]
    print(f"  {meth:<6}: 训练 1 次（节省 {cv_calls}x）  "
          f"10x 内达标率 {h10:>5.0f}%   100x 内达标率 {h100:>5.0f}%")

print()
print("=" * 118)
print("指标 4：SRS 是否比最好的廉价基线更好？")
print("=" * 118)
srs = np.array([r["srs"] for r in rows])
ch = np.array([min(r["b1"], r["b2"], r["b3"]) for r in rows])
win = srs <= ch
print(f"  SRS 优于三个廉价基线的组数: {int(win.sum())}/{len(rows)} = {win.mean()*100:.1f}%")
print(f"  SRS 误差中位 {np.median(srs):.3e}  vs  最佳廉价基线中位 {np.median(ch):.3e}")
print(f"  改善倍数（中位）: {np.median(ch)/max(np.median(srs),1e-300):.1f}x")

json.dump(dict(absolute=summ, hit_rate=hit,
               srs_win_rate=float(win.mean()),
               srs_err_med=float(np.median(srs)),
               cheap_best_err_med=float(np.median(ch)),
               improvement=float(np.median(ch) / max(np.median(srs), 1e-300)),
               cv_calls=cv_calls),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
