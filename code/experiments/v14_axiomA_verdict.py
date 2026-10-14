# -*- coding: utf-8 -*-
"""决定性判读（补充）：区分「真实依赖」与「微小数值漂移导致的虚假相关」。

判据：
  · 若 alpha_cov ∝ Delta，则比值 alpha_cov/Delta 应近似常数。
  · 实测比值跨度 2.26x（几乎等于 Delta 自身的跨度 2.27x），
    说明**分子不变、分母变化**——即 alpha_cov 与 Delta 无关。
"""
import io, json
import numpy as np

p = r"E:\deepseekworkspace\experiments_v12\v14_axiomA_cov.json"
rows = json.load(io.open(p, encoding="utf-8"))
D = np.array([r["Delta"] for r in rows])
A = np.array([r["alpha_cov"] for r in rows])
R = A / D

print("=" * 96)
print("决定性判读：alpha_cov 是否随 Delta 变化？")
print("=" * 96)
print(f"  {'n':>4}{'Delta':>12}{'alpha_cov':>14}{'ratio':>12}")
for r in rows:
    print(f"  {r['n']:>4}{r['Delta']:>12.4f}{r['alpha_cov']:>14.6f}{r['ratio']:>12.6f}")

print()
print("  关键量：")
print(f"    Delta      变化 {D.min():.4f} -> {D.max():.4f}   跨度 {D.max()/D.min():.3f}x")
print(f"    alpha_cov  变化 {A.min():.6f} -> {A.max():.6f}   跨度 {A.max()/A.min():.5f}x")
print(f"    比值       变化 {R.min():.6f} -> {R.max():.6f}   跨度 {R.max()/R.min():.3f}x")
print()
print("  判读：")
print(f"    Delta 变化 {D.max()/D.min():.2f} 倍，而 alpha_cov 只变化 {A.max()/A.min():.5f} 倍")
print(f"    -> alpha_cov 与 Delta **无关**（若相关，两者跨度应同量级）")
print(f"    Pearson 相关 {np.corrcoef(D, A)[0,1]:+.4f} 由 {A.ptp():.2e} 量级的数值漂移产生，不可采信")
print()
print("  对照：若 alpha_cov ∝ Delta，应观察到")
print(f"    alpha_cov 跨度 ≈ {D.max()/D.min():.2f}x，即 {A.min():.6f} -> {A.min()*D.max()/D.min():.6f}")

print()
print("=" * 96)
print("与 Axiom A 定理的对照")
print("=" * 96)
print("  定理（已证，Baladi-Gouezel 2009 等）：alpha_res ≍ Delta")
print("  - alpha_res 是 **Ruelle 共振逼近率**（各向异性 Banach 空间）")
print(f"  本检验：alpha_cov（协方差谱指数）不随 Delta 变化")
print("  => 在真 Axiom A 系统上，协方差谱指数与 Lyapunov 隙**解耦**")
print("  => 这**支持稿件**的核心判断：alpha 不是 Lyapunov 量")
print()
print("  但必须标注的局限：")
print("  · 猫映射是**线性**的，其协方差谱几乎退化，alpha_cov 由可观测量光滑度主导")
print("  · 因此本检验证明的是『alpha_cov 不受 Delta 控制』，而非『alpha_cov = alpha_res』")
print("  · 严格的 alpha_res 数值需要各向异性 Banach 空间上的 Ruelle 共振计算（未做）")
