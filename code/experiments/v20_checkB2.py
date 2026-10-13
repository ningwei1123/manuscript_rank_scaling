# -*- coding: utf-8 -*-
"""V20 严格检验 B（修正版）。

修正：KS 用了固定 dt=0.02，但线性项 −k²−k⁴ 的最大模随 N² 增长，
      N=128 时刚性比太大导致发散。改为 dt 随 N 自适应：
          dt ≈ 0.4 · 2.77 / k_max²   （满足 dt·k⁴ 足够小）
"""
import io, os, json
import numpy as np
from scipy.linalg import svd as csvd

OUT = r"E:\deepseekworkspace\experiments_v12"


def rank_relF(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


EPS = np.array([1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4])


def ks(N, L0=11.0, T=250.0, sample=6, seed=11, burn=60.0):
    """积分因子法；dt 随 N 自适应以控制刚性。"""
    kmax = np.pi * N / (2 * np.pi * L0)          # 最大波数
    dt = min(0.02, 0.3 / max(kmax ** 2, 1.0))
    x = 2 * np.pi * L0 * np.arange(N) / N
    u = np.cos(x / L0) * (1 + 0.1 * np.sin(x / (2 * L0)))
    u += 0.001 * np.random.default_rng(seed).standard_normal(N)
    k = np.fft.rfftfreq(N, d=(2 * np.pi * L0 / N))
    Lk = -k ** 2 - k ** 4
    ik = 1j * k
    E = np.exp(Lk * dt); E2 = np.exp(Lk * dt / 2)

    def nl(uu):
        return -0.5 * ik * np.fft.rfft(uu ** 2)

    def step(u):
        uh = np.fft.rfft(u)
        a = nl(u)
        u1 = np.real(np.fft.irfft(E2 * (uh + 0.5 * dt * a), N))
        b = nl(u1)
        return np.real(np.fft.irfft(E * uh + dt * E2 * b, N))

    nb = int(burn / dt); nst = int(T / dt)
    for _ in range(nb):
        u = step(u)
    out = []
    for i in range(nst):
        u = step(u)
        if i % sample == 0:
            out.append(u.copy())
    X = np.array(out)[200:]
    if not np.all(np.isfinite(X)):
        return None
    return X


print("=" * 108)
print("B1 Kuramoto–Sivashinsky：模态数 N 可调（能分辨真实第三类吗？）")
print("=" * 108)
print(f"  {'N':>5}{'dt':>8}{'样本':>7}" + "".join(f"{'ε='+format(e,'g'):>10}" for e in EPS)
      + f"{'max/min':>10}  封顶?")
print("-" * 108)
KS = {}
for N in (16, 32, 64, 128):
    X = ks(N)
    if X is None:
        print(f"  {N:>5}   积分失败"); continue
    KS[N] = X
    lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
    r = rank_relF(lam, EPS)
    ratio = r.max() / r.min()
    kmax = np.pi * N / (2 * np.pi * 11.0)
    dt = min(0.02, 0.3 / max(kmax ** 2, 1.0))
    print(f"  {N:>5}{dt:>8.4f}{X.shape[0]:>7}" + "".join(f"{int(v):>10}" for v in r)
          + f"{ratio:>10.2f}  {'是' if ratio < 1.35 else '否'}")
print("-" * 108)


def rk4(fn, x, dt):
    k1 = fn(x); k2 = fn(x + .5*dt*k1); k3 = fn(x + .5*dt*k2); k4 = fn(x + dt*k3)
    return x + dt/6*(k1 + 2*k2 + 2*k3 + k4)


def l96_traj(N, ns, every=6, dt=0.005, burn=20000):
    f = lambda x: (np.roll(x, -1) - np.roll(x, 2)) * np.roll(x, 1) - x + 8.0
    x = 8 + 0.01 * np.random.default_rng(1).standard_normal(N)
    for _ in range(burn):
        x = rk4(f, x, dt)
    X = np.empty((ns, N))
    for i in range(ns):
        for _ in range(every):
            x = rk4(f, x, dt)
        X[i] = x
    return X


print("\n" + "=" * 108)
print("B2 Lorenz-96 大尺寸（N 从 40 到 2000）")
print("=" * 108)
print(f"  {'N':>6}{'样本':>8}" + "".join(f"{'ε='+format(e,'g'):>10}" for e in EPS)
      + f"{'max/min':>10}  封顶?   样本是否充分")
print("-" * 108)
L96 = {}
for N, ns in ((40, 60000), (100, 40000), (200, 30000), (500, 15000), (1000, 9000), (2000, 6000)):
    X = l96_traj(N, ns)
    L96[N] = X
    lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
    r = rank_relF(lam, EPS)
    ratio = r.max() / r.min()
    print(f"  {N:>6}{X.shape[0]:>8}" + "".join(f"{int(v):>10}" for v in r)
          + f"{ratio:>10.2f}  {'是' if ratio < 1.35 else '否':<8}"
          f"{'充分' if ns > 10*N else '偏少(M<N×10)'}")
print("-" * 108)

R = {}
for tag, DD in (("KS", KS), ("L96", L96)):
    for n, X in DD.items():
        lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
        r = rank_relF(lam, EPS)
        R[f"{tag}_{n}"] = dict(n=n, M=int(X.shape[0]), r=r.tolist(),
                               ratio=float(r.max()/r.min()),
                               rank_hi=int(r[0]), rank_lo=int(r[-1]))
json.dump(R, io.open(os.path.join(OUT, "v20_check_B.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nsaved v20_check_B.json")
