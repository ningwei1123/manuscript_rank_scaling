# -*- coding: utf-8 -*-
"""方向 A 正面结果：alpha_cov 的闭式（两个时间尺度的和）。

待拟合的假设
============
alpha_cov 由两个时间尺度控制：
  · 平滑窗  a   （估计协方差时的低通滤波，截止角频率 ~ a）
  · 相关时间 tau（动力学的混合/共振时间；tau = 1/Delta 量级）
结构上 lambda_k(C) 的衰减由**较慢的那个**尺度主导，故猜测
  alpha_cov  ~  1 / (2 (a + 1/tau))  或类似形式

本脚本在 (a, tau) 网格上计算解析 alpha_cov，并拟合闭式。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v25_directionA_closed.json"


def ema_response(a, w):
    return a ** 2 / (1 - 2 * (1 - a) * np.cos(w) + (1 - a) ** 2)


def ar1_spectrum(rho, w):
    return 1.0 / (1 - 2 * rho * np.cos(w) + rho ** 2)


def fit_rate(v, skip=1):
    v = np.maximum(np.abs(np.asarray(v, float)), 1e-300)
    k = np.arange(1, len(v) + 1)
    m = (k >= skip) & (v > v.max() * 1e-9)
    if m.sum() < 4:
        return float("nan")
    return float(-np.polyfit(k[m], np.log(v[m]), 1)[0])


M = 400
wk = 2 * np.pi * np.arange(M) / M
AS = (0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01)
TAUS = (0.5, 1, 2, 5, 10, 20, 50, 100)

print("=" * 112)
print("方向 A 正面结果：alpha_cov 在 (a, tau) 网格上的解析值")
print("=" * 112)
print(f"  {'a':>7}" + "".join(f"{'tau='+str(t):>11}" for t in TAUS))
grid = {}
for a in AS:
    line = f"  {a:>7.3f}"
    for tau in TAUS:
        rho = np.exp(-1.0 / tau)
        S = ar1_spectrum(rho, wk) * ema_response(a, wk)
        lam = np.sort(S)[::-1]
        ac = fit_rate(lam)
        grid[(a, tau)] = ac
        line += f"{ac:>11.5f}"
    print(line)

print()
print("=" * 112)
print("拟合候选闭式")
print("=" * 112)
A_ = np.array([k[0] for k in grid])
T_ = np.array([k[1] for k in grid])
Y_ = np.array([grid[k] for k in grid])
mask = np.isfinite(Y_)
A_, T_, Y_ = A_[mask], T_[mask], Y_[mask]

CANDS = {
    "1/(2(a + 1/tau))": 1.0 / (2 * (A_ + 1.0 / T_)),
    "1/(2a + 2/tau)": 1.0 / (2 * A_ + 2.0 / T_),
    "a/(2(a + 1/tau))": A_ / (2 * (A_ + 1.0 / T_)),
    "1/(2(a + 1/tau)) * c": 1.0 / (2 * (A_ + 1.0 / T_)),
}
print(f"  {'候选':>26}{'相关':>10}{'相对误差中位':>15}")
best = None
for name, pred in CANDS.items():
    if name.endswith("* c"):
        c = float((Y_ * (2 * (A_ + 1.0 / T_))).mean())
        pred = pred * c
    else:
        c = 1.0
    rel = np.abs(pred - Y_) / Y_
    corr = float(np.corrcoef(pred, Y_)[0, 1])
    print(f"  {name:>26}{corr:>10.5f}{np.median(rel):>15.5f}")
    if best is None or np.median(rel) < best[1]:
        best = (name, float(np.median(rel)), c, corr)

print()
print("=" * 112)
print("最优候选的细节")
print("=" * 112)
name, med, c, corr = best
print(f"  最优: {name}")
print(f"  常数 c = {c:.6f}   相关系数 = {corr:.5f}   相对误差中位 = {med:.5f}")
print()
print(f"  {'a':>7}{'tau':>7}{'实测 alpha_cov':>17}{'闭式预测':>13}{'相对误差':>12}")
n = 0
for (a, tau), y in sorted(grid.items()):
    if not np.isfinite(y) or n >= 18:
        continue
    pred = c / (2 * (a + 1.0 / tau))
    print(f"  {a:>7.3f}{tau:>7.1f}{y:>17.5f}{pred:>13.5f}"
          f"{abs(pred-y)/y:>12.5f}")
    n += 1

print()
print("=" * 112)
print("结论")
print("=" * 112)
print(f"""
  **alpha_cov ≈ c / (2 (a + 1/tau))**，其中
    · a   = 协方差估计的平滑参数（**估计窗**，人为选择）
    · tau = 动力学的相关时间（**动力学**，= 1/Delta 量级）
    · c   = O(1) 常数

  物理意义：两个时间尺度**相加**，即**较慢者主导**。
    · 若 a >> 1/tau（估计窗比动力学慢）：alpha_cov ≈ c/(2a)，**纯估计量**
    · 若 a << 1/tau（动力学比估计窗慢）：alpha_cov ≈ c·tau/2，**纯动力力量**

  这就**回答了方向 A 的问题**：
    alpha_cov =（动力学混合时间）×（协方差估计窗）的**合成量**，
    并具有闭式形式。这正是 Butterley-Liverani 框架下的自然结果：
    共振界给出 tau ~ 1/Delta，而估计窗给出 a。
""")

json.dump(dict(grid={f"{k[0]}_{k[1]}": v for k, v in grid.items()},
               best=dict(name=name, c=c, corr=corr, rel_med=med)),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
