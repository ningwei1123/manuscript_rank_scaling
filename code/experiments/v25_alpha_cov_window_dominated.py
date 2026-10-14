# -*- coding: utf-8 -*-
"""方向 A 严格验证：alpha_cov 是否与动力学无关（滤波器主导）？

待检验的两个论断
================
论断 1（不变性）：alpha_cov 只依赖 (观测量的谱形, 协方差估计的时间平滑窗)，
                  **不依赖** Lyapunov 指数 Delta。
论断 2（可解析预测）：alpha_cov 可由"平滑后的功率谱" S~(omega) = |H(omega)|^2 S(omega)
                     在 M 个频率上的采样 lam_k = S~(omega_k) 预测。

验证设计
========
· 用 **多轨道** 估计协方差（而非单轨道的 Toeplitz），避免上一步的噪声问题
· 每个 (Delta, a, 可观测量) 组合重复多个种子 => 报告均值与标准差
· 扫描 Delta（n=2,3,5）与 a（0.5,0.2,0.05,0.01）
· 关键检验：固定 a，alpha_cov 是否随 Delta 变化？
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v25_directionA_strict.json"


def cat_orbit(A, T, x0, burn=3000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = (A @ x) % 1.0
    X = np.empty((T, 2))
    for t in range(T):
        x = (A @ x) % 1.0
        X[t] = x
    return X


def ema(x, a):
    y = np.empty_like(x)
    acc = x[0].copy()
    for t in range(len(x)):
        acc = (1 - a) * acc + a * x[t]
        y[t] = acc
    return y


def cov_spectrum(X, n_snap=400):
    """用 n_snap 个时间点的状态向量构造协方差，返回其特征值（降序）。"""
    Z = X[:n_snap] - X[:n_snap].mean(0, keepdims=True)
    C = (Z.T @ Z) / max(n_snap - 1, 1)
    return np.sort(np.linalg.eigvalsh(C))[::-1]


def fit_rate(v, skip=1):
    v = np.abs(np.asarray(v, float))
    v = np.maximum(v, 1e-300)
    k = np.arange(1, len(v) + 1)
    m = (k >= skip) & (v > v.max() * 1e-9)
    if m.sum() < 3:
        return float("nan")
    return float(-np.polyfit(k[m], np.log(v[m]), 1)[0])


print("=" * 112)
print("方向 A 严格验证：alpha_cov 是否与 Delta 无关？")
print("=" * 112)
print("  协方差 = 滤波后轨道的**空间**协方差（2 维）——不够，改用延迟嵌入")
print()

# 用延迟嵌入：把滤波后的标量序列嵌入到 M 维，构造 M×M 协方差
def delay_cov(f, M):
    N = len(f) - M + 1
    Z = np.empty((N, M))
    for j in range(M):
        Z[:, j] = f[j:j + N]
    Z = Z - Z.mean(0, keepdims=True)
    C = (Z.T @ Z) / max(N - 1, 1)
    return np.sort(np.linalg.eigvalsh(C))[::-1]


print(f"  {'n':>4}{'Delta':>9}{'a(EMA)':>8}{'M':>6}"
      f"{'alpha_cov 均值':>16}{'标准差':>11}{'alpha_cov/Delta':>17}")
rows = []
for nA in (2, 3, 5):
    A = np.array([[nA, 1.0], [nA - 1, 1.0]])
    mu1 = (np.trace(A) + np.sqrt(np.trace(A) ** 2 - 4)) / 2
    Delta = float(np.log(mu1))
    for a in (0.5, 0.2, 0.05, 0.01):
        vals = []
        for sd in range(6):
            rng = np.random.default_rng(100 + sd)
            X = cat_orbit(A, 6000, rng.random(2))
            f = np.cos(2 * np.pi * X[:, 0])
            f = f - f.mean()
            fe = ema(f, a)
            fe = fe - fe.mean()
            w = delay_cov(fe, 60)
            vals.append(fit_rate(w))
        vals = np.array([v for v in vals if np.isfinite(v)])
        m, s = float(vals.mean()), float(vals.std())
        rows.append(dict(n=nA, Delta=Delta, a=a, alpha_cov=m, std=s,
                         ratio=m / Delta))
        print(f"  {nA:>4}{Delta:>9.4f}{a:>8.3f}{60:>6}{m:>16.6f}{s:>11.6f}"
              f"{m/Delta:>17.6f}")

print()
print("=" * 112)
print("关键检验：固定 a，alpha_cov 是否随 Delta 变化？")
print("=" * 112)
for a in (0.5, 0.2, 0.05, 0.01):
    sub = [r for r in rows if r["a"] == a]
    acs = [r["alpha_cov"] for r in sub]
    ds = [r["Delta"] for r in sub]
    print(f"  a={a:<6} alpha_cov = {min(acs):.6f} .. {max(acs):.6f}  "
          f"（跨度 {max(acs)/min(acs):.3f}×）  Delta 跨度 {max(ds)/min(ds):.3f}×")

print()
print("=" * 112)
print("判读")
print("=" * 112)
print("""
  若「固定 a 时 alpha_cov 的跨度 << Delta 的跨度」，
  则 alpha_cov 与 Delta **基本无关** => 支持"alpha_cov 是滤波器量"的论断。
""")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
