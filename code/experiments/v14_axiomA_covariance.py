# -*- coding: utf-8 -*-
"""决定性检验（修正方法）：在真 Axiom A 系统上计算**协方差谱指数** α_cov，
   并与 Lyapunov 隙 Δ 比较。

之前的方法错误：测了 Ulam 转移算子的特征值。
猫映射的 Koopman 算子在 L² 上酉，Ulam 特征值全在单位圆上 —— 测不到衰减。

正确方法：
  1. 生成猫映射的长轨道
  2. 用一个解析可观测量（Fourier 特征）构造快照
  3. 计算**协方差矩阵的特征值**（这才是稿件测的量）
  4. 拟合其衰减指数 α_cov
  5. 与 Δ 比较

Axiom A 定理预测 α_res ≍ Δ（共振逼近率）。
若 α_cov 也 ≍ Δ，则稿件"α 与 Δ 无关"是**错的**；
若 α_cov 与 Δ 无关，则稿件是对的，且说明两个 α 确实不同。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v14_axiomA_cov.json"


def cat_matrix(n):
    """[[n,1],[n-1,1]]，det=1，n>=2 时双曲（Axiom A）。"""
    return np.array([[n, 1.0], [n - 1, 1.0]])


def lyap(A):
    ev = np.abs(np.linalg.eigvals(A))
    ev = np.sort(ev)[::-1]
    l1, l2 = np.log(ev[0]), np.log(ev[1])
    return float(l1), float(l2), float(l1 - l2), float(ev[0])


def orbit(A, T, x0, burn=1000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = (A @ x) % 1.0
    X = np.empty((T, 2))
    for t in range(T):
        x = (A @ x) % 1.0
        X[t] = x
    return X


def cov_spectrum(X, n_lags=1):
    """由轨道构造快照矩阵，返回协方差特征值（降序）。
    n_lags：用多少个延迟坐标（1 = 只用当前状态）。"""
    T = X.shape[0]
    if n_lags == 1:
        S = X
    else:
        S = np.stack([X[i:T - n_lags + 1 + i] for i in range(n_lags)], axis=1)
        S = S.reshape(S.shape[0], -1)
    Y = S - S.mean(0, keepdims=True)
    C = (Y.T @ Y) / (Y.shape[0] - 1)
    w = np.linalg.eigvalsh(C)[::-1]
    return np.maximum(w, 0)


def obs_features(X, K=64):
    """解析可观测量：Fourier 特征 exp(2 pi i k.x)，k 取小整数向量。
    返回实值快照（实部与虚部分开），构成 2K 个通道的延迟嵌入。"""
    ks = []
    for k1 in range(-3, 4):
        for k2 in range(-3, 4):
            if (k1, k2) != (0, 0):
                ks.append((k1, k2))
    ks = ks[:K // 2]
    feats = []
    for (k1, k2) in ks:
        ph = 2 * np.pi * (k1 * X[:, 0] + k2 * X[:, 1])
        feats.append(np.cos(ph))
        feats.append(np.sin(ph))
    return np.stack(feats, axis=1)


def fit_exp_rate(w):
    """拟合特征值的指数衰减率 alpha（log w 对 index 线性）。"""
    w = np.asarray(w, float)
    m = w > 1e-14
    if m.sum() < 10:
        return None, None
    idx = np.arange(len(w))[m]
    lw = np.log(w[m])
    s = np.polyfit(idx, lw, 1)
    r2 = 1 - ((lw - np.polyval(s, idx)) ** 2).sum() / ((lw - lw.mean()) ** 2).sum()
    return float(-s[0]), float(r2)


print("=" * 108)
print("决定性检验：Axiom A 系统上 协方差谱指数 alpha_cov  vs  Lyapunov 隙 Delta")
print("=" * 108)
print(f"  {'n':>4}{'mu1=e^l1':>11}{'Delta=l1-l2':>14}{'alpha_cov':>12}"
      f"{'alpha_cov/Delta':>17}{'R2':>8}")
rows = []
T = 60000
for n in (2, 3, 4, 5, 6, 8):
    A = cat_matrix(n)
    l1, l2, D, mu1 = lyap(A)
    X = orbit(A, T, (0.3141, 0.2718))
    F = obs_features(X, K=64)
    w = cov_spectrum(F, n_lags=1)
    a, r2 = fit_exp_rate(w)
    if a is None:
        print(f"  {n:>4}{mu1:>11.4f}{D:>14.6f}{'拟合失败':>12}")
        continue
    rows.append(dict(n=n, mu1=mu1, Delta=D, alpha_cov=a,
                     ratio=(a / D if D else None), r2=r2))
    print(f"  {n:>4}{mu1:>11.4f}{D:>14.6f}{a:>12.6f}{a/D:>17.4f}{r2:>8.4f}")

print()
print("=" * 108)
print("判读")
print("=" * 108)
if len(rows) >= 3:
    Ds = np.array([r["Delta"] for r in rows])
    As = np.array([r["alpha_cov"] for r in rows])
    corr = float(np.corrcoef(Ds, As)[0, 1])
    s = np.polyfit(Ds, As, 1)
    r2 = 1 - ((As - np.polyval(s, Ds)) ** 2).sum() / ((As - As.mean()) ** 2).sum()
    ratios = np.array([r["ratio"] for r in rows])
    print(f"  alpha_cov 范围        : {As.min():.6f} .. {As.max():.6f}")
    print(f"  Delta 范围            : {Ds.min():.4f} .. {Ds.max():.4f}")
    print(f"  相关系数 corr(Delta, alpha_cov) = {corr:+.4f}")
    print(f"  线性拟合 alpha_cov = {s[0]:.6f}*Delta + {s[1]:.6f}   R2={r2:.4f}")
    print(f"  alpha_cov/Delta 比值  : {ratios.min():.6f} .. {ratios.max():.6f}  "
          f"(跨度 {ratios.max()/ratios.min():.2f}x)")
    print()
    if abs(corr) > 0.9:
        print("  => alpha_cov 与 Delta 强相关：**稿件'alpha 与 Delta 无关'的结论受到挑战**")
    elif abs(corr) < 0.5:
        print("  => alpha_cov 与 Delta 不相关：**支持稿件，且证实两个 alpha 不同**")
    else:
        print("  => 相关性中等，证据不足以判定")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
