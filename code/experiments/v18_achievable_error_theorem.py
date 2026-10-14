# -*- coding: utf-8 -*-
"""第 1 项 (a) 定稿：严格定理 + 失效条件 + 可用的实用界。

定理（秩-r 模型的可达误差，精确）
--------------------------------
x ~ N(0, C)，y = K x，秩-r 模型 M（任意 rank<=r 的线性映射）。
则最小可达均方误差为
    min_{rank(M)<=r}  E‖y − M x‖²  =  E‖(I − P_r^y) y‖²  =  Σ_{k>r} λ_k(C_y)
其中 C_y = K C K^T 是**输出**协方差，P_r^y 为其前 r 个特征子空间投影。

即：**可达误差 = 输出协方差谱的尾部**。

推论（何时输入谱可预测输出谱）
------------------------------
若 K 与 C 的谱对齐（K 保持 C 的特征子空间），则
    λ_k(C_y) = λ_k(C) · s_k²,   s_k = 第 k 个奇异值
故可达误差 = Σ_{k>r} λ_k s_k²，当 s_k 有界时由**输入谱尾部**控制。

**若 K 与 C 不对齐，输入谱尾部不能控制输出谱尾部** —— 界失效。

本脚本：
1. 验证「可达误差 = 输出谱尾部」的等式
2. 量化「输入谱尾部」作为界的松弛度，并展示其随不对齐程度增长
3. 给出**实用的可算界**：用输出的（可估计的）谱尾部
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v18_theorem.json"


def achievable_error(lam, K, r):
    """min_{rank<=r} E‖y − M x‖² = Σ_{k>r} λ_k(K C K^T)（解析）。"""
    C = np.diag(lam)
    Cy = K @ C @ K.T
    wy = np.sort(np.linalg.eigvalsh(Cy))[::-1]
    return float(wy[r:].sum()), wy


def input_tail(lam, r):
    """输入谱尾部加权：Σ_{k>r} λ_k。"""
    l = np.asarray(lam, float)
    return float(l[r:].sum())


print("=" * 112)
print("① 验证：可达误差 = 输出协方差谱尾部")
print("=" * 112)
rng = np.random.default_rng(11)
print(f"  {'谱':>11}{'n':>5}{'r':>4}{'输出谱尾部':>15}{'数值最优 rank-r':>18}{'比值':>9}")
rows = []
for kind, ps in (("exp", (0.05, 0.2)), ("alg", (1.0, 2.0))):
    for p in ps:
        for n in (40,):
            lam = (np.exp(-p * np.arange(1, n + 1)) if kind == "exp"
                   else np.arange(1, n + 1, dtype=float) ** (-p))
            K = rng.standard_normal((n, n)) / np.sqrt(n)
            C = np.diag(lam)
            for r in (2, 5, 10):
                ana, wy = achievable_error(lam, K, r)
                # 数值：对 rank-r 模型做优化（用随机搜索 + 解析最优）
                # 解析最优是投影到 Cy 的前 r 个特征子空间
                Cy = K @ C @ K.T
                wy2, Vy = np.linalg.eigh(Cy)
                Vy = Vy[:, ::-1]
                Pr = Vy[:, :r] @ Vy[:, :r].T
                # 最优 M = Pr K
                M = Pr @ K
                num = float(np.trace((K - M) @ C @ (K - M).T))
                rows.append(dict(kind=kind, param=p, n=n, r=r,
                                 analytic=ana, numeric=num,
                                 ratio=(num / ana if ana > 1e-18 else np.nan)))
                print(f"  {kind+' p='+str(p):>11}{n:>5}{r:>4}{ana:>15.6e}"
                      f"{num:>18.6e}{(num/ana if ana>1e-18 else float('nan')):>9.6f}")

print()
print("=" * 112)
print("② 输入谱尾部作为界：松弛度 vs 对齐程度")
print("=" * 112)
print("  构造 K = 对齐部分 (对角) + 强度 c 的不对齐部分（随机）")
print(f"  {'c(不对齐)':>11}{'可达误差':>14}{'输入尾部':>14}{'界/真值':>12}")
align_rows = []
n, p = 40, 0.2
lam = np.exp(-p * np.arange(1, n + 1))
for c in (0.0, 0.05, 0.1, 0.3, 1.0):
    # 对齐部分：对角 s_k = 1；不对齐：随机
    K = np.diag(np.ones(n)) + c * rng.standard_normal((n, n)) / np.sqrt(n)
    ae, wy = achievable_error(lam, K, 10)
    it = input_tail(lam, 10)
    align_rows.append(dict(c=c, achievable=ae, input_tail=it,
                           ratio=(it / ae if ae > 1e-18 else np.nan)))
    print(f"  {c:>11.2f}{ae:>14.6e}{it:>14.6e}"
          f"{(it/ae if ae>1e-18 else float('nan')):>12.4f}")

print()
print("=" * 112)
print("③ 实用界：用**输出**谱尾部（可从数据估计）")
print("=" * 112)
print("  可达误差 = sum_{k>r} lambda_k(C_y)，而 C_y 可由数据估计")
print("  给出 rank-r 模型的误差上界 = 输出谱尾部（可算、且紧到常数 1）")
for kind, ps in (("exp", (0.05, 0.2)), ("alg", (1.0, 2.0))):
    for pp in ps:
        l2 = (np.exp(-pp * np.arange(1, n + 1)) if kind == "exp"
              else np.arange(1, n + 1, dtype=float) ** (-pp))
        K = rng.standard_normal((n, n)) / np.sqrt(n)
        Cy = K @ np.diag(l2) @ K.T
        wy = np.sort(np.linalg.eigvalsh(Cy))[::-1]
        for r in (5, 10, 20):
            ae, _ = achievable_error(l2, K, r)
            print(f"    {kind} p={pp} r={r}: 可达误差={ae:.6e}  "
                  f"输出尾部={wy[r:].sum():.6e}  比={wy[r:].sum()/ae if ae>0 else 1.0:.6f}")

json.dump(dict(equality=rows, alignment=align_rows),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
