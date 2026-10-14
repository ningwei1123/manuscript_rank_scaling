# -*- coding: utf-8 -*-
"""路 B 步骤 3：alpha_cov 与 Delta 的关系——尝试**推导**指数。

目标：解释 alpha_cov ~ Delta^{-0.64}

推导尝试
========
设自协方差 R(t) = a^{|t|}（a = e^{-Delta}），Toeplitz 阶 n。
谱密度（Szego/Grenander）：
    S(omega) = (1-a^2) / |1 - a e^{i omega}|^2
Toeplitz 特征值 lam_k ≈ S(omega_k)，omega_k = 2 pi k / n。

**关键**：lam_k 的**排序**与 omega_k 的**排序**不同！
S(omega) 在 omega = 0 处最大，故排序后 lam_1 = S(0)，且排序索引与
"频率从 0 向外"一致（因 S 在 [0,pi] 上单调降）。

于是 lam_k ≈ S(2 pi (k-1) / n)，即
    lam_k ∝ 1 / |1 - a e^{i 2 pi (k-1)/n}|^2

对 k << n/2（低频）：
    |1 - a e^{i theta}|^2 = 1 - 2a cos theta + a^2
    小 theta 展开：≈ (1-a)^2 + a theta^2
故
    lam_k ≈ (1-a^2) / [ (1-a)^2 + a (2 pi (k-1)/n)^2 ]

令 k_c = n(1-a) / (2 pi sqrt(a)) 为"拐点"。
· k << k_c：lam_k ≈ (1-a^2)/(1-a)^2 = 常数（**平坦**）
· k >> k_c：lam_k ≈ (1-a^2) n^2 / (4 pi^2 a (k-1)^2) ~ k^{-2}（**代数**）

=> **alpha_cov 不是单一指数**：谱是"平坦 + 代数尾部"的折线！
   用单一指数拟合该折线，得到的 alpha_cov 依赖 k_c 的位置，即依赖 (n, Delta)。

本脚本：导出闭式，检验 alpha_cov 与 (n, Delta) 的关系，解释 -0.64。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v28_alpha_derivation.json"


def toeplitz_eigs(a, n):
    idx = np.arange(n)
    return np.sort(np.linalg.eigvalsh(a ** np.abs(idx[:, None] - idx[None, :])))[::-1]


def fit_exp(v, skip=2):
    v = np.maximum(np.asarray(v, float), 1e-300)
    k = np.arange(1, len(v) + 1)
    m = (k >= skip) & (v > v.max() * 1e-12)
    return float(-np.polyfit(k[m], np.log(v[m]), 1)[0]) if m.sum() >= 5 else np.nan


def S_theory(a, n):
    """解析谱密度在 n 个等间隔频率上的采样（降序）。"""
    k = np.arange(n)
    th = 2 * np.pi * k / n
    S = (1 - a ** 2) / np.abs(1 - a * np.exp(1j * th)) ** 2
    return np.sort(S)[::-1]


print("=" * 112)
print("路 B 步骤 3：alpha_cov ~ Delta^{-0.64} 的推导")
print("=" * 112)
print()
print("  解析谱密度 S(omega) = (1-a^2)/|1 - a e^{i omega}|^2，omega_k = 2 pi k/n")
print("  拐点 k_c = n(1-a) / (2 pi sqrt(a))")
print()
print(f"  {'Delta':>7}{'a':>9}{'n':>6}{'k_c':>9}{'alpha_cov':>12}{'k_c/n':>9}{'区域':>10}")
rows = []
for n in (32, 64, 128, 256):
    for Delta in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0):
        a = np.exp(-Delta)
        kc = n * (1 - a) / (2 * np.pi * np.sqrt(a))
        lam = toeplitz_eigs(a, n)
        ac = fit_exp(lam)
        zone = "平坦" if kc > n else ("代数尾" if kc < 3 else "过渡")
        rows.append(dict(n=n, Delta=Delta, a=float(a), kc=float(kc),
                         alpha_cov=float(ac), kc_over_n=float(kc / n), zone=zone))
        if Delta in (0.1, 1.0, 3.0):
            print(f"  {Delta:>7.3f}{a:>9.5f}{n:>6}{kc:>9.2f}{ac:>12.6f}"
                  f"{kc/n:>9.4f}{zone:>10}")

print()
print("=" * 112)
print("检验①：解析 S(omega_k) 是否等于 Toeplitz 特征值？")
print("=" * 112)
for n, Delta in ((64, 0.5), (64, 1.0), (128, 0.2)):
    a = np.exp(-Delta)
    lam = toeplitz_eigs(a, n)
    St = S_theory(a, n)
    rel = np.abs(lam - St) / np.maximum(np.abs(lam), 1e-300)
    print(f"  n={n:<5} Delta={Delta:<5} 相对偏差中位 {np.median(rel):.5f}  "
          f"最大 {rel.max():.5f}")

print()
print("=" * 112)
print("检验②：alpha_cov 对 Delta 的幂律指数（固定 n）")
print("=" * 112)
print(f"  {'n':>6}{'拟合指数 p (alpha ~ Delta^p)':>32}{'R²':>10}")
for n in (32, 64, 128, 256, 512):
    sub = [r for r in rows if r["n"] == n]
    D = np.array([r["Delta"] for r in sub])
    A = np.array([r["alpha_cov"] for r in sub])
    m = np.isfinite(A) & (A > 0)
    s = np.polyfit(np.log(D[m]), np.log(A[m]), 1)
    r2 = 1 - ((np.log(A[m]) - np.polyval(s, np.log(D[m]))) ** 2).sum() / \
             ((np.log(A[m]) - np.log(A[m]).mean()) ** 2).sum()
    print(f"  {n:>6}{s[0]:>32.4f}{r2:>10.5f}")

print()
print("=" * 112)
print("判读")
print("=" * 112)
print("""
  · **alpha_cov 不是单一指数**。解析谱 S(omega_k) 是
      「低频平坦 + 高频 omega^{-2} 代数尾」的折线，
    拐点 k_c = n(1-a)/(2 pi sqrt(a)) 随 (n, Delta) 移动。
  · 用**单一指数**拟合这条折线，得到的 alpha_cov 因此依赖 k_c 的位置。
  · 这解释了为何 alpha_cov：
      - 依赖 Delta（通过 k_c）
      - 依赖估计窗 n（通过 k_c）
      - 且**不满足简单的闭式**（因为折线的拟合没有闭式）
  · 故幂指数 -0.64 是**折线拟合的产物**，不是普适常数。
""")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
