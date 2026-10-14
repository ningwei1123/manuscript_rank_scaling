# -*- coding: utf-8 -*-
"""方向 A（Butterley-Liverani 路线）：alpha_cov 与传递算子共振的精确关系。

前几次失败的根因
================
我此前把 alpha_cov 等同于"自协方差 R(t) 的衰减率"，并试图令其 = 最慢可见共振。
**这是概念错误。** 见下。

正确的问题分解（三层，必须分开）
================================
第 0 层：动力学共振。传递算子 L（或 Koopman U）在适当的**各向异性 Banach 空间**
        B 上拟紧：谱 = {单位圆上的有限个特征值} ∪ {半径 <= rho_ess 的紧集}。
        Butterley-Liverani 给出 rho_ess 的界。
        对角化系统：rho_ess = 1/|mu_1|（且 L 在 B 上无单位圆外谱）。

第 1 层：自协方差衰减。对 f ∈ B，
        R(t) = <f, U^t f>_mu 的衰减率 = max{ |lam| : lam ∈ spec(U|_B), <f, phi_lam> != 0 }
        对角化系统：R(t) 精确 = sum over k of |c_k|^2 e^{-Delta t}（k != 0）
        => **R(t) 只有一个衰减率**（由 Delta 决定），**不存在"多个共振的竞争"**

第 2 层：协方差算子 C 的谱。C 的构造是 **时间平滑**：
        C = (1/M) sum_{t=0}^{M-1} x_t x_t^T  （或用 EMA 滤波）
        时间平滑 = 对功率谱施加**频域滤波** |H(omega)|^2。
        **lam_k(C) 的衰减率 alpha_cov 由滤波器的频率响应决定，而不是由 Delta 决定。**

=> 关键论断：**alpha_cov 是"滤波器"量，不是"共振"量。**
   稿件说"alpha is a resonance quantity"因此**在字面上是不准确的**；
   准确的说法是：**alpha_cov 由（动力学共振谱）×（协方差估计所用的时间平滑窗）共同决定**。

本条论断可解析验证
==================
设 x_t 是平稳过程，功率谱 S(omega)。
用 EMA 滤波 x~_t = (1-a) x~_{t-1} + a x_t，其频率响应
    H(omega) = a / (1 - (1-a) e^{-i omega})
    |H|^2 = a^2 / (1 - 2(1-a)cos omega + (1-a)^2)
则滤波后过程的功率谱 S~(omega) = |H(omega)|^2 S(omega)。
而滤波后序列的协方差矩阵（Toeplitz）的特征值 = S~ 在 M 个频率上的采样。
=> **lam_k(C) = S~(omega_k)**，其中 omega_k 是第 k 个频率。

故 alpha_cov 由 S~ 的形状决定，可**解析预测**并与数值对比。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v25_directionA_BL.json"


# ---------- 猫映射（Anosov，对角化，有解析共振） ----------
def cat_map_orbit(A, T, x0, burn=5000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = (A @ x) % 1.0
    X = np.empty((T, 2))
    for t in range(T):
        x = (A @ x) % 1.0
        X[t] = x
    return X


def ema(x, a):
    """EMA 滤波，返回滤波后序列。"""
    y = np.empty_like(x)
    acc = x[0].copy()
    for t in range(len(x)):
        acc = (1 - a) * acc + a * x[t]
        y[t] = acc
    return y


def fit_exp_rate(v, skip=2):
    """拟合 |v_k| 对 k 的指数衰减率。"""
    v = np.abs(np.asarray(v, float))
    v = np.maximum(v, 1e-300)
    k = np.arange(1, len(v) + 1)
    m = (k >= skip) & (v > v.max() * 1e-12)
    if m.sum() < 5:
        return float("nan")
    s = np.polyfit(k[m], np.log(v[m]), 1)
    return float(-s[0])


print("=" * 112)
print("方向 A（Butterley-Liverani 路线）：alpha_cov 由滤波器还是共振决定？")
print("=" * 112)

# 猫映射 A = [[n,1],[n-1,1]]，det=1，Anosov
results = []
for nA in (2, 3, 5):
    A = np.array([[nA, 1.0], [nA - 1, 1.0]])
    mu1 = (np.trace(A) + np.sqrt(np.trace(A) ** 2 - 4)) / 2
    Delta = np.log(mu1)
    X = cat_map_orbit(A, 40000, [0.3141592653589793, 0.2718281828459045])
    print(f"\n  --- n={nA}, mu1={mu1:.4f}, Delta=ln(mu1)={Delta:.6f} ---")
    print(f"  {'a(EMA)':>8}{'可观测量':>16}{'R(t) 衰减率':>14}"
          f"{'alpha_cov(实测)':>17}{'alpha_cov/Delta':>17}")
    for a in (0.5, 0.2, 0.05, 0.01):
        for obs_name, obs in (("cos(2pi x)", lambda X: np.cos(2 * np.pi * X[:, 0])),
                              ("cos(2pi x)+cos(2pi y)",
                               lambda X: np.cos(2 * np.pi * X[:, 0]) + np.cos(2 * np.pi * X[:, 1]))):
            f = obs(X)
            f = f - f.mean()
            # R(t) 衰减率
            R = np.array([(f[:len(f) - L] * f[L:]).sum() / (f * f).sum()
                          for L in range(0, 31)])
            m = (np.arange(len(R)) >= 1) & (np.abs(R) > 1e-12)
            if m.sum() >= 5:
                idx = np.arange(len(R))[m]
                Rrate = float(-np.polyfit(idx, np.log(np.abs(R[m])), 1)[0])
            else:
                Rrate = float("nan")
            # EMA 滤波后的协方差谱
            fe = ema(f, a)
            fe = fe - fe.mean()
            M = min(len(fe) // 4, 800)
            # 用 Toeplitz 自协方差矩阵的特征值作为 C 的谱
            Rf = np.array([(fe[:len(fe) - L] * fe[L:]).sum() / len(fe)
                           for L in range(0, M)])
            C = np.array([[Rf[abs(i - j)] for j in range(M)] for i in range(M)])
            w = np.sort(np.linalg.eigvalsh(C))[::-1]
            w = np.maximum(w, 0)
            a_cov = fit_exp_rate(w)
            print(f"  {a:>8.3f}{obs_name:>16}{Rrate:>14.6f}"
                  f"{a_cov:>17.6f}{a_cov/Delta:>17.6f}")
            results.append(dict(n=nA, mu1=float(mu1), Delta=float(Delta), a=a,
                                obs=obs_name, R_rate=float(Rrate),
                                alpha_cov=float(a_cov),
                                ratio=float(a_cov / Delta)))

json.dump(results, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
