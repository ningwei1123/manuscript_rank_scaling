# -*- coding: utf-8 -*-
"""路 1 (A)：本地按 PDEBench 设置生成 1D Advection / Burgers，
并检验「协方差谱指数 -> 判类」是否跟随。

PDEBench 1D Advection 设置（论文 arXiv:2210.07182）：
    u_t + beta * u_x = 0,  x in [0, 1), 周期边界
    初值为平滑随机场，其谱由 beta 参数化（beta 越大越平滑）
    网格 N = 1024，步长按 CFL 取

本脚本的控制点：初值谱指数 p 是**已知输入**，故协方差谱指数可解析预测，
判据的正确行为是「谱指数变 -> 判类跟随」。
"""
import io, os, json, time
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v13_pde_local.json"
rng = np.random.default_rng(20260212)
N = 1024


def pdebench_ic_from_beta(beta, n_modes=64, seed=0):
    """PDEBench 风格初值：谱幅度 ~ k^{-beta}，随机相位。"""
    r = np.random.default_rng(seed)
    k = np.arange(1, n_modes + 1)
    amp = k ** (-beta)
    ph = r.uniform(0, 2 * np.pi, n_modes)
    x = np.linspace(0, 1, N, endpoint=False)
    u = np.zeros(N)
    for kk, a, p in zip(k, amp, ph):
        u += a * np.cos(2 * np.pi * kk * x + p)
    return u - u.mean()


def advect(u0, beta, n_steps, dt):
    """周期域上的线性平流：u_t + beta u_x = 0（谱方法，精确）。"""
    k = 2 * np.pi * np.fft.rfftfreq(N, d=1.0 / N)
    uh = np.fft.rfft(u0)
    phase = np.exp(-1j * beta * k * dt)
    snaps = np.empty((n_steps, N))
    for i in range(n_steps):
        uh = uh * phase
        snaps[i] = np.fft.irfft(uh, N)
    return snaps


def burgers(u0, nu, n_steps, dt):
    """1D Burgers：u_t + u u_x = nu u_xx（谱方法 + 去混叠）。"""
    k = 2 * np.pi * np.fft.rfftfreq(N, d=1.0 / N)
    dealias = (np.abs(k) < (2.0 / 3.0) * np.max(np.abs(k)))
    u = u0.copy()
    snaps = np.empty((n_steps, N))
    for i in range(n_steps):
        uh = np.fft.rfft(u)
        nl = -0.5 * 1j * k * np.fft.rfft(np.fft.irfft(uh, N) ** 2)
        nl[~dealias] = 0.0
        uh = (uh + dt * nl) / (1.0 + nu * k ** 2 * dt)
        u = np.fft.irfft(uh, N)
        snaps[i] = u
    return snaps


def cov_spec(snaps, w=None):
    Y = snaps - snaps.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / max(Y.shape[0] - 1, 1)


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def classify(lam, eps_lo=0.3, eps_hi=1e-4):
    """返回 (谱类, 秩类, 谱指数, 秩指数, 一致性)。"""
    lam = np.sort(lam)[::-1]; n = len(lam); k = np.arange(1, n + 1)
    pos = lam > 1e-16
    le = np.log(lam[pos])
    se = np.polyfit(k[pos], le, 1)
    r2e = 1 - ((le - np.polyval(se, k[pos])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    sa = np.polyfit(np.log(k[pos]), le, 1)
    r2a = 1 - ((le - np.polyval(sa, np.log(k[pos]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    eps = np.logspace(np.log10(eps_lo), np.log10(eps_hi), 60)
    r = ranks(lam, eps)
    m = r < n * 0.999
    if m.sum() < 8:
        m = np.ones_like(r, bool)
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / ((r[m] - r[m].mean()) ** 2).sum()
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    r2p = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / ((lg - lg.mean()) ** 2).sum()
    sc = "EXP" if r2e > r2a else "ALG"
    rc = "ALG" if r2p > r2l else "EXP"
    return sc, rc, float(-sa[0]), float(pp[0]), (sc == rc), float(r2e), float(r2a), float(r2l), float(r2p)


print("=" * 116)
print("路 1 (A)：本地 1D Advection（PDEBench 设置）")
print("=" * 116)
print("  谱指数 p 为已知输入（初值幅度 ~ k^{-p}）；预测协方差谱指数 beta = p")
print()
print(f"  {'beta_in':>8}{'beta_fit':>10}{'谱类':>7}{'秩类':>7}{'一致':>6}"
      f"{'秩指数':>9}{'理论 1/(p-1/2)':>17}{'源图':>7}")
res = {}
t0 = time.time()
for beta_in in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
    u0 = pdebench_ic_from_beta(beta_in, n_modes=64, seed=int(beta_in * 100))
    # 平流速度取 1，步长使总时间 = 1 个周期
    snaps = advect(u0, beta=1.0, n_steps=1200, dt=1.0 / 1200)
    lam = cov_spec(snaps)
    sc, rc, bfit, rexp, agree, r2e, r2a, r2l, r2p = classify(lam)
    theory = 1 / (beta_in - 0.5) if beta_in > 0.5 else float("inf")
    res[f"advection_beta{beta_in}"] = dict(
        beta_in=beta_in, beta_fit=bfit, spec_class=sc, rank_class=rc, agree=bool(agree),
        rank_exp=rexp, theory=None if not np.isfinite(theory) else theory,
        r2_spec_exp=r2e, r2_spec_alg=r2a, r2_rank_log=r2l, r2_rank_pow=r2p,
        n_modes=64, n_steps=1200, N=N)
    ts = "inf" if not np.isfinite(theory) else f"{theory:.3f}"
    print(f"  {beta_in:>8.2f}{bfit:>10.4f}{sc:>7}{rc:>7}{'✓' if agree else '✗':>6}"
          f"{rexp:>9.4f}{ts:>17}{len(snaps):>7}")

print()
print("=" * 116)
print("路 1 (A)：本地 1D Burgers")
print("=" * 116)
print(f"  {'nu':>7}{'beta_fit':>10}{'谱类':>7}{'秩类':>7}{'一致':>6}{'秩指数':>9}")
for nu in (0.01, 0.05, 0.1, 0.2):
    u0 = pdebench_ic_from_beta(1.0, n_modes=32, seed=int(nu * 1000))
    snaps = burgers(u0, nu=nu, n_steps=800, dt=2e-4)
    lam = cov_spec(snaps)
    sc, rc, bfit, rexp, agree, r2e, r2a, r2l, r2p = classify(lam)
    res[f"burgers_nu{nu}"] = dict(nu=nu, beta_fit=bfit, spec_class=sc, rank_class=rc,
                                  agree=bool(agree), rank_exp=rexp,
                                  r2_spec_exp=r2e, r2_spec_alg=r2a,
                                  r2_rank_log=r2l, r2_rank_pow=r2p)
    print(f"  {nu:>7.3f}{bfit:>10.4f}{sc:>7}{rc:>7}{'✓' if agree else '✗':>6}{rexp:>9.4f}")

json.dump(res, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n耗时 {time.time()-t0:.0f}s；已保存 {OUT}")
