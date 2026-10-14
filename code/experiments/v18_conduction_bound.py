# -*- coding: utf-8 -*-
"""第 1 项 (a) 修正：C-相对算子范数形式的分辨率界。

推导
----
设定：x ~ N(0, C)，y = K x，秩-r 模型 M_r = P_r K P_r。
绝对误差：
    E‖y − M_r x‖² = E‖(K − P_r K P_r) x‖²
                   = tr( (K − P_r K P_r) C (K − P_r K P_r)^T )

关键分解（严格）：
    K − P_r K P_r = (I−P_r) K P_r + (I−P_r) K (I−P_r) + P_r K (I−P_r)

三项的 C-加权范数分别由谱尾部控制。令
    Q_r = I − P_r,   tail(r) = ( tr(Q_r C Q_r) )^{1/2} = ( Σ_{k>r} λ_k )^{1/2}
则
    tr((I−P_r) K C K^T (I−P_r))  <=  ‖K‖_{C→2}² · tail(r)²

故**绝对误差界**：
    sqrt( E‖y − M_r x‖² )  <=  ‖K‖_{C} · tail(r)
其中 ‖K‖_{C} := ‖ C^{1/2} K^T C^{−1/2} ‖_2 是 **C-相对算子范数**
（即 K 作为 C-加权算子的范数，等价于 C^{−1/2} y 与 C^{−1/2} x 的典型相关系数上界）。

与相对误差的关系：
    sqrt(E‖y − M_r x‖² / E‖y‖²)  =  该界 / ‖K‖_C-weighted total
    => 相对误差 <= tail(r) / ‖C^{1/2}‖_F   （当 K 为等距时取等）

本脚本验证**绝对形式**的界是否成立且紧。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v18_conduction2.json"


def abs_error_exact(lam, K, r):
    """E‖y − M_r x‖² 的精确值（高斯 x）。"""
    C = np.diag(lam)
    n = len(lam)
    Pr = np.zeros((n, n)); Pr[:r, :r] = np.eye(r)
    A = K - Pr @ K @ Pr
    return float(np.sqrt(np.trace(A @ C @ A.T)))


def tail_norm(lam, r):
    """tail(r) = sqrt(Σ_{k>r} λ_k)。"""
    l = np.asarray(lam, float)
    return float(np.sqrt(l[r:].sum()))


def c_relative_norm(lam, K):
    """‖K‖_C = ‖ C^{1/2} K^T C^{−1/2} ‖_2。"""
    l = np.asarray(lam, float)
    n = len(l)
    C12 = np.diag(np.sqrt(l))
    Cm12 = np.diag(1.0 / np.sqrt(l))
    return float(np.linalg.norm(C12 @ K.T @ Cm12, 2))


print("=" * 112)
print("绝对误差界： sqrt(E‖y − M_r x‖²) <= ‖K‖_C · tail(r) ？")
print("=" * 112)
print(f"  {'谱':>12}{'n':>5}{'r':>4}{'实测绝对误差':>16}{'界':>14}{'界/实测':>11}")
rng = np.random.default_rng(7)
rows = []
for kind, params in (("exp", (0.05, 0.2, 0.5)), ("alg", (1.0, 2.0, 3.0))):
    for p in params:
        for n in (40, 100):
            if kind == "exp":
                lam = np.exp(-p * np.arange(1, n + 1))
            else:
                lam = np.arange(1, n + 1, dtype=float) ** (-p)
            for trial in range(4):
                K = rng.standard_normal((n, n)) / np.sqrt(n)
                kn = c_relative_norm(lam, K)
                for r in (2, 5, 10, 20):
                    if r >= n:
                        continue
                    ae = abs_error_exact(lam, K, r)
                    bd = kn * tail_norm(lam, r)
                    rows.append(dict(kind=kind, param=p, n=n, r=r, trial=trial,
                                     actual=ae, bound=bd,
                                     ratio=(bd / ae if ae > 1e-15 else np.inf)))
                    if trial == 0:
                        print(f"  {kind+' p='+str(p):>12}{n:>5}{r:>4}{ae:>16.6f}"
                              f"{bd:>14.6f}{(bd/ae if ae>1e-15 else float('nan')):>11.4f}")

rt = np.array([r["ratio"] for r in rows if np.isfinite(r["ratio"])])
print()
print("=" * 112)
print("汇总")
print("=" * 112)
print(f"  样本数 {len(rt)}")
print(f"  界/实测: 中位 {np.median(rt):.4f}  范围 {rt.min():.4f} .. {rt.max():.4f}")
print(f"  界是否恒成立（>=1）？ {bool((rt >= 1 - 1e-9).all())}")
print(f"  平均松弛倍数: {rt.mean():.3f}")
print()
print("  若界恒成立且松弛为 O(1) => **可用的可证误差界**")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
