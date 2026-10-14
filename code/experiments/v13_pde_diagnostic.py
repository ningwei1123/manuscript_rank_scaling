# -*- coding: utf-8 -*-
"""决定性诊断：本地 1D Advection 的协方差谱指数与秩指数，是什么关系？

不再猜测约定——直接打印：
  · 协方差特征值本身（前 10 与后 10）
  · 用哪一种归一化得到的秩曲线
  · 秩曲线的**两种**幂指数（用 sqrt 与不用 sqrt）
"""
import numpy as np

rng = np.random.default_rng(20260212)
N = 1024


def ic(beta, n_modes=64, seed=0):
    r = np.random.default_rng(seed)
    k = np.arange(1, n_modes + 1)
    amp = k ** (-beta)
    ph = r.uniform(0, 2 * np.pi, n_modes)
    x = np.linspace(0, 1, N, endpoint=False)
    u = np.zeros(N)
    for kk, a, p in zip(k, amp, ph):
        u += a * np.cos(2 * np.pi * kk * x + p)
    return u - u.mean()


def advect(u0, beta=1.0, n_steps=1200, dt=1.0 / 1200):
    k = 2 * np.pi * np.fft.rfftfreq(N, d=1.0 / N)
    uh = np.fft.rfft(u0)
    ph = np.exp(-1j * beta * k * dt)
    out = np.empty((n_steps, N))
    for i in range(n_steps):
        uh = uh * ph
        out[i] = np.fft.irfft(uh, N)
    return out


def cov(snaps):
    Y = snaps - snaps.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / (Y.shape[0] - 1), sv


p = 1.0
u0 = ic(p, seed=100)
snaps = advect(u0)
lam, sv = cov(snaps)
print("=" * 104)
print(f"输入初值幅度指数 p = {p}")
print("=" * 104)
print(f"  奇异值前 8 : {np.round(sv[:8], 4)}")
print(f"  特征值前 8 : {np.round(lam[:8], 6)}")
print()

# 谱指数拟合
k = np.arange(1, len(lam) + 1)
pos = lam > 1e-16
sa = np.polyfit(np.log(k[pos]), np.log(lam[pos]), 1)
print(f"  log(lambda) vs log(k) 斜率 = {sa[0]:.4f}  ->  lambda ~ k^{{{sa[0]:.3f}}}")
# 若 lam = A k^{-q}，则初值幅度 ~ k^{-q/2}；输入 p=1 => 期望 q=2
print(f"  期望：lam ~ k^{{-2p}} = k^{{{-2*p:.1f}}}  ->  斜率应为 {-2*p:.1f}")
print(f"  实测斜率 {sa[0]:.4f}  =>  2p_eff = {-sa[0]:.4f}, p_eff = {-sa[0]/2:.4f}")
print()

# 秩曲线的两种归一化
def ranks_sqrt(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def ranks_energy(lam, eps):
    lam = np.sort(lam)[::-1]
    rel = np.maximum(1 - np.cumsum(lam) / lam.sum(), 0)
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


eps = np.logspace(np.log10(0.3), np.log10(1e-4), 60)
for name, fn in (("sqrt 归一化 (Frobenius)", ranks_sqrt), ("能量归一化", ranks_energy)):
    r = fn(lam, eps)
    m = r < len(lam) * 0.999
    if m.sum() < 8:
        m = np.ones_like(r, bool)
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    r2 = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / ((lg - lg.mean()) ** 2).sum()
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / ((r[m] - r[m].mean()) ** 2).sum()
    print(f"  {name:<26} 秩指数={pp[0]:.4f} (R²={r2:.4f})   对数律 R²={r2l:.4f}   "
          f"r(1e-3)={int(fn(lam,[1e-3])[0])}")
print()
print(f"  理论（若谱指数为 {2*p:.1f}）: 1/({2*p:.1f} - 0.5) = {1/(2*p-0.5):.4f}")
print(f"  理论（若谱指数为 {p:.1f}）: 1/({p:.1f} - 0.5) = {1/(p-0.5):.4f}")
