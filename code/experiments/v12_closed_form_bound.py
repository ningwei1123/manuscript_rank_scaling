# -*- coding: utf-8 -*-
"""路 2 的真实发现：闭式是精确秩的上界，偏差有显式界。"""
import numpy as np


def r_exact(alpha, n, eps):
    e2 = np.exp(-2 * alpha * np.arange(n))
    tot = e2.sum()
    return next(r for r in range(n + 1) if e2[r:].sum() <= eps ** 2 * tot)


def R_closed(alpha, n, eps):
    return (1 / (2 * alpha)) * np.log((1 - np.exp(-2 * alpha * n)) /
                                      (eps ** 2 * (1 - np.exp(-2 * alpha)))) + 1


print("=" * 100)
print("闭式 vs 精确秩（0-based 谱，alpha*n 大）")
print("=" * 100)
hdr = f"  {'alpha':>7}{'n':>8}{'eps':>9}{'精确 r*':>9}{'闭式 R':>10}{'R-r*':>8}{'相对%':>9}"
print(hdr)
mx = 0.0
rows = []
for alpha in (0.01, 0.02, 0.05, 0.1, 0.2, 0.4):
    bound = (1.0 / (2 * alpha)) * np.log(1.0 / (1 - np.exp(-2 * alpha)))
    for n in (2000, 100000):
        for eps in (0.1, 0.02, 0.005, 0.001):
            re_ = r_exact(alpha, n, eps)
            R = R_closed(alpha, n, eps)
            gap = R - re_
            mx = max(mx, gap)
            rows.append((alpha, n, eps, re_, R, gap, bound))
            rel = (gap / re_ * 100) if re_ else 0.0
            print(f"  {alpha:>7.3f}{n:>8}{eps:>9.4f}{re_:>9}{R:>10.3f}{gap:>8.3f}{rel:>8.1f}%")

print()
print("=" * 100)
print("核验")
print("=" * 100)
allup = all(r[4] >= r[3] - 1e-9 for r in rows)
allbnd = all(r[5] <= r[6] + 1e-6 for r in rows)
print(f"  闭式是否始终 >= 精确秩 : {allup}")
print(f"  最大偏差 R - r*        : {mx:.3f}")
print(f"  偏差是否被 (1/2a)ln(1/(1-e^-2a)) 界住 : {allbnd}")
print()
print("  对 alpha 很小时该界约为 ln(1/(2a))/(2a)，说明闭式在高精度要求下高估所需秩。")
print("  这是一个**有利于设计**的偏差方向：按闭式选秩不会欠拟合。")
