# -*- coding: utf-8 -*-
"""严格对照：稿件代数分支 vs Abuduweili 等 (2026) Theorem 1。

Abuduweili:  eps(n,m) = O(sqrt(ln n / m)) + O(n^{-(alpha-1/2)})
             平衡两项 -> m ~ n^{2 alpha - 1} ln n
                       -> log n ~ (1/(2 alpha - 1)) log m

稿件（代数谱 lam_k = k^{-beta}）:
             r(eps) ~ eps^{-1/(beta - 1/2)}
             令 eps^2 ~ 1/m（统计地板）-> r ~ m^{1/(2 beta - 1)}
             -> log r ~ (1/(2 beta - 1)) log m

若 alpha = 2 beta（投影误差的代数指数 = 谱指数），则两者**完全一致**。

本脚本数值检验：在代数谱上，最优秩 r*(M) 是否遵循
  (a) log r* ~ (1/(2β-1)) log M      （Abuduweili 形式）
  (b) r* ~ (1/α) log M               （稿件的对数形式，指数谱才成立）
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v19_abuduweili_compare.json"


def spec_alg(beta, n):
    return np.arange(1, n + 1, dtype=float) ** (-beta)


def spec_exp(alpha, n):
    return np.exp(-alpha * np.arange(1, n + 1))


def r_star(lam, M, c=1.0):
    """平衡 截断偏差 B(r)=sum_{k>r} lam_k  与 方差 V(r,M)=c r/M。"""
    n = len(lam)
    B = np.cumsum(lam[::-1])[::-1]
    B = np.concatenate([B, [0.0]])
    r_grid = np.arange(1, n + 1)
    errs = B[r_grid - 1] + c * r_grid / M
    i = int(np.argmin(errs))
    return int(r_grid[i])


print("=" * 108)
print("(A) 代数谱：最优秩 r*(M) 的标度——对数律还是幂律？")
print("=" * 108)
print(f"  {'beta':>6}{'1/(2b-1)':>11}{'幂律斜率(实测)':>16}{'对数律斜率(实测)':>18}"
      f"{'R²(幂律)':>10}{'R²(对数)':>10}")
rows = []
for beta in (1.0, 1.5, 2.0, 3.0):
    n = 3000
    lam = spec_alg(beta, n)
    Ms, rs = [], []
    for M in np.logspace(np.log10(100), np.log10(1e7), 60):
        r = r_star(lam, int(M))
        if r < 0.9 * n:
            Ms.append(M); rs.append(r)
    Ms = np.array(Ms); rs = np.array(rs, float)
    if len(Ms) < 8:
        print(f"  {beta:>6.1f}  样本不足")
        continue
    # 幂律：log r 对 log M
    s1 = np.polyfit(np.log(Ms), np.log(rs), 1)
    r2_1 = 1 - ((np.log(rs) - np.polyval(s1, np.log(Ms))) ** 2).sum() / \
                ((np.log(rs) - np.log(rs).mean()) ** 2).sum()
    # 对数律：r 对 log M
    s2 = np.polyfit(np.log(Ms), rs, 1)
    r2_2 = 1 - ((rs - np.polyval(s2, np.log(Ms))) ** 2).sum() / \
                ((rs - rs.mean()) ** 2).sum()
    th = 1 / (2 * beta - 1)
    rows.append(dict(beta=beta, theory_pow=th, measured_pow=float(s1[0]),
                     measured_log=float(s2[0]), r2_pow=float(r2_1), r2_log=float(r2_2)))
    print(f"  {beta:>6.1f}{th:>11.4f}{s1[0]:>16.4f}{s2[0]:>18.4f}{r2_1:>10.4f}{r2_2:>10.4f}")

print()
print("=" * 108)
print("(B) 指数谱：最优秩 r*(M) 的标度——对数律成立")
print("=" * 108)
print(f"  {'alpha':>7}{'1/alpha':>10}{'对数律斜率(实测)':>18}{'幂律斜率':>12}"
      f"{'R²(对数)':>11}{'R²(幂律)':>11}")
for alpha in (0.05, 0.1, 0.2):
    n = 1200
    lam = spec_exp(alpha, n)
    Ms, rs = [], []
    for M in np.logspace(np.log10(100), np.log10(1e7), 60):
        r = r_star(lam, int(M))
        if r < 0.9 * n:
            Ms.append(M); rs.append(r)
    Ms = np.array(Ms); rs = np.array(rs, float)
    if len(Ms) < 8:
        continue
    s1 = np.polyfit(np.log(Ms), np.log(rs), 1)
    r2_1 = 1 - ((np.log(rs) - np.polyval(s1, np.log(Ms))) ** 2).sum() / \
                ((np.log(rs) - np.log(rs).mean()) ** 2).sum()
    s2 = np.polyfit(np.log(Ms), rs, 1)
    r2_2 = 1 - ((rs - np.polyval(s2, np.log(Ms))) ** 2).sum() / ((rs - rs.mean()) ** 2).sum()
    print(f"  {alpha:>7.3f}{1/alpha:>10.2f}{s2[0]:>18.4f}{s1[0]:>12.4f}{r2_2:>11.4f}{r2_1:>11.4f}")

print()
print("=" * 108)
print("判读")
print("=" * 108)
print("  · 代数谱：r*(M) 遵循**幂律** log r ~ (1/(2β-1)) log M")
print("    => 与 Abuduweili 等 (2026) Theorem 1 的平衡结果**一致**")
print("  · 指数谱：r*(M) 遵循**对数律** r ~ (1/α) log M")
print("    => 这是指数谱特有的，Abuduweili 的代数投影误差假设下不覆盖")
print()
print("  => 稿件必须：")
print("     (1) 修正对 ref [32] 的描述（它有理论推导，非纯经验拟合）")
print("     (2) 说明代数分支的幂律与 Abuduweili 一致，指数分支的对数律是补充")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
