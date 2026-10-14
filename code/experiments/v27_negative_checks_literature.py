# -*- coding: utf-8 -*-
"""负面结论 10 遍检验（第 2 部分：N1-N5, N7, N10 + 文献反查）。"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v27_negative_checks2.json"
res = {}

# ============================================================
print("=" * 112)
print("[N10 反查] 秩选择真的无算法空间？——寻找反例")
print("=" * 112)
print("  陈述：谱已知时 r* = min{r : 尾和 <= eps^2} 是定义，无算法空间。")
print("  反例候选：若'可达误差'不是尾和（例如目标不是重建误差），则空间存在。")
print()
print("  检验：对'预测'目标（y = Kx 的一步预测），可达误差 = 输出协方差尾部和。")
print("        输入尾部 != 输出尾部（除非 A = cQ）。")
print("        => 此时'用输入谱做秩选择'是一个**近似**，存在算法空间。")
print()
rng = np.random.default_rng(3)
n = 50
lam = np.exp(-0.15 * np.arange(1, n + 1))
C = np.diag(lam)
print(f"  {'misalign':>10}{'eps':>7}{'输入尾部秩':>13}{'输出尾部和秩':>15}{'差':>7}")
for mis in (0.0, 0.05, 0.2, 0.5):
    Qb, _ = np.linalg.qr(rng.standard_normal((n, n)))
    A = Qb + mis * rng.standard_normal((n, n)) / np.sqrt(n)
    Cin = C
    Cout = A @ C @ A.T


    def r_of(M, eps):
        w = np.sort(np.linalg.eigvalsh(M))[::-1]
        w = np.maximum(w, 0)
        c = np.cumsum(w) / max(w.sum(), 1e-300)
        idx = np.where(1 - c <= eps ** 2)[0]
        return int(idx[0] + 1) if len(idx) else n


    for eps in (0.05,):
        ri, ro = r_of(Cin, eps), r_of(Cout, eps)
        print(f"  {mis:>10.2f}{eps:>7.2f}{ri:>13}{ro:>15}{ro-ri:>7}")
print()
print("  => 若输入/输出尾部秩差异显著，则'用输入谱选秩'是**近似**，")
print("     存在一个**修正项**的算法空间（方向 B 的一阶修正即此）。")
print("     故 N10 的严格形式是：**对重建目标无空间，对预测目标有空间**。")

# ============================================================
print()
print("=" * 112)
print("[N1 反查] 宽度幂律不可能：是定理还是我读过头了？")
print("=" * 112)
print("""  Lanthaler-Stuart (2023) Theorem 2.11 原文要点（本机库）：
    "the continuous nonlinear n-widths ... decay at most (poly-)logarithmically in n"
  即：对**一般 Lipschitz 算子**，n-width 至多对数衰减
      => 达到精度 eps 所需规模随 1/eps **指数**增长，不是幂律。

  **但**：这只排除"对一般算子存在幂律"。
  对**特定**算子类（如谱指数衰减的），幂律**是可能的**：
    稿件自己的代数分支 r ~ eps^{-1/(beta-1/2)} 就是幂律。
  故 N1 的严格形式是：
    "不存在**对所有** Lipschitz 算子统一的宽度幂律"
    而非"宽度律不可能是幂律"。
  稿件现有表述（"a power law in width is unavailable for operators of this generality"）
  已含 "of this generality"，**表述正确**。
""")
res["N1_verdict"] = "表述正确（已限定 'of this generality'）"

# ============================================================
print("=" * 112)
print("[N2 反查] 宽度幂指数 1.97->3.47 漂移：是物理还是测量窗口不足？")
print("=" * 112)
print("""  漂移的可能来源：
  (a) 物理：指数本身不稳定
  (b) 测量：训练宽度范围不足，落在饱和区
  (c) 测量：训练预算不足，模型未收敛

  稿件已报告 (c)：'a budget study over a fivefold range of training epochs'
  并称 'the fitted exponent moves from 1.97 to 3.47 ... it does not settle'

  **关键检验**：若把宽度范围**扩大**，指数是否稳定？
  （本机无 GPU 训练环境，无法做此检验）

  => N2 的严格形式应限于："在**我们扫描的宽度与预算范围内**指数不稳定"。
     不能断言"指数本身不存在"。稿件现有 "the width branch is not established"
     是**恰当的弱主张**。但需明确它是**范围限定**的。
""")
res["N2_verdict"] = "需明确为范围限定；不能断言指数不存在"

# ============================================================
print("=" * 112)
print("[N3 反查] KS 不一致 4-82%：是结构还是窗口选择的产物？")
print("=" * 112)
print("""  我已做的检验（上一轮）：7 个 alpha 窗口，偏差 3.7% - 81.6%，")
  且 corr(R², |R-1|) = -0.205（拟合越好不一定越一致）。

  **反查问题**：如果一个"正确的"窗口选择规则存在，偏差会收敛吗？
  已检验的 7 个窗口包括全谱（最宽）到 15-25（最窄）。最宽窗口给 3.7%。
  => 存在一个窗口给 3.7%（与理论一致），但**无先验规则**选出它。
  => N3 的严格形式："偏差依赖窗口选择，且无先验规则确定窗口"
     这是**方法论**结论，不是"理论被证伪"。
  稿件现有表述（报告范围 + 说明窗口）**恰当**。
""")
res["N3_verdict"] = "表述恰当（方法论结论，非证伪）"

# ============================================================
print("=" * 112)
print("[N4 反查] 三向比较不可识别：我的合成对照是否充分？")
print("=" * 112)
print("""  我的对照：'synthetic spectra with 20 to 50 dominant modes reproduce the same disagreement'
  N = 14（7 区域 x 2 产品）。

  **反查**：14 个样本、29% 一致率，是否只是**统计功效不足**？
  二项检验：若真实一致率为 50%，观测 4/14 的 p 值？
""")
from math import comb
N_, k_ = 14, 4
p_obs = sum(comb(N_, i) * 0.5 ** N_ for i in range(0, k_ + 1))
print(f"  若 H0: 一致率 = 0.5，观测 <= 4/14 的单尾 p = {p_obs:.5f}")
print(f"  => {'拒绝 H0' if p_obs < 0.05 else '不能拒绝 H0'}")
print("""  但**关键**是：我的合成对照（20-50 主导模态）**已复现**同样的低一致率，
  说明低一致率可由**有限样本谱**解释，不需要域外失效。
  => N4 的严格形式：'在本样本量下不可识别'（已如此表述）
  稿件现有表述 **恰当**。
""")
res["N4_verdict"] = f"表述恰当；二项 p={p_obs:.5f}"

# ============================================================
print("=" * 112)
print("[N5 反查] 对齐条件 A = cQ：一般算子不满足——是否过于苛刻而失去用途？")
print("=" * 112)
print("""  我的推导：T_out/T_in 与 r 无关 <=> A = cQ。
  **反查**：这个条件在**实际**算子学习中成立吗？
  · 若 K 是学出来的算子，A = K 一般**不是** cQ
  · 故 N5 意味着：**输入谱一般不能给出可达误差**

  **但有更弱、更有用的条件**：若 A 只**近似**保持 C 的**前 r 个**特征子空间
  （而非全部），则 T_out(r) ≈ T_in(r) 对**该 r** 成立。
  这比 A = cQ 弱得多，且是**逐 r** 的条件。

  => N5 的严格形式应分两层：
     (i)  **对所有 r** 成立 <=> A = cQ（严格）
     (ii) **对某个给定 r** 近似成立 <= 前 r 个特征子空间近似不变（弱，实用）
  稿件只报告了 (i)，**应补 (ii)**——这是本反查发现的**实质改进点**。
""")
res["N5_verdict"] = "严格条件正确，但应补逐-r 的弱条件"

json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
