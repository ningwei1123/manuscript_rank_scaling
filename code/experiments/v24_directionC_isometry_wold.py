# -*- coding: utf-8 -*-
"""方向 C：理论结论（放弃 Ulam 数值验证，记录失败）。

理论（有文献支撑，可严格陈述）
============================
命题 C1. 若 T 保测，则 U f = f∘T 是 L²(μ) 上的等距：||Uf|| = ||f||。
   [直接来自保测性：∫|f∘T|² dμ = ∫|f|² dμ]
命题 C2. U 是酉 ⟺ T 可逆（在标准概率空间上）。
命题 C3. 等距的谱在单位圆上 ⟹ 「Koopman 无衰减谱」只需保测性。
命题 C4. T 不可逆时，Wold 分解给出 L² = H_u ⊕ H_s，
   H_u 为酉部分（对应可逆分量），H_s 为移位部分（不可逆性的载体）。

文献依据（本机库原文）
====================
· Colbrook (2021) ResDMD:
  "suppose that K : L2(Ω,ω) → L2(Ω,ω) is an **isometry**, then there exists a
   **unitary extension** K' defined on an extended Hilbert space H' with L2 ⊂ H'"
  ⟹ 等距可扩展为酉，故谱仍在单位圆上。
· Anton_Colbrook_EDMD_expanding_maps:
  "merely an **isometry** and can thus be decomposed into a **unitary** and a
   **shift** part by means of the **Wold decomposition**"
  **且**："the relevant rates of correlation decay **cannot be obtained from the
   spectrum of the unitary evolution operator**"
· Giannakis (2017):
  "the Koopman and Perron-Frobenius operators are **unitary and adjoint** to one another"
· Brunton et al. (2022):
  "relations are required to hold for **non-invertible maps** or on closed subsets"

对稿件的含义
============
稿件目前说「Koopman 算子是酉」。**更准确的是「等距」**：
  · 保测 ⟹ 等距（充分，且只需此）
  · 保测 + 可逆 ⟹ 酉
故核心主张的适用范围**可以且应当**扩大到不可逆保测系统。

**但**：我的 Ulam 数值验证**连续失败四次**，失败模式如下
--------------------------------------------------------
① 把 Perron-Frobenius（前推）当作 Koopman（前拉）
② 用 cell-center 采样构造 Ulam —— 盒的像不落在盒上，破坏等距
③ 误以为 dyadic 分划是 doubling 映射的 Markov 分划
   （实际 [0,1/N) 与 [1/2, 1/2+1/N) 都映到 [0,2/N)，故列和不为常数）
④ 修正后仍 max|U^T U/N − I| ≈ 0.998（N=1024），即仍非等距

**结论：该数值验证在本轮未能完成。理论陈述依赖文献，不依赖我的数值。**
**若要在稿件中使用，应引用 Colbrook (2021) 的 unitary extension，
而非声称有独立的数值验证。**
"""
import io, json

OUT = r"E:\deepseekworkspace\experiments_v12\v24_direction_C_final.json"

CONCLUSIONS = {
    "propositions": [
        {"id": "C1", "statement": "T 保测 ⟹ U f = f∘T 是 L²(μ) 上的等距",
         "status": "theorem", "proof": "∫|f∘T|²dμ = ∫|f|²dμ（保测性）",
         "literature": "Colbrook (2021): isometry"},
        {"id": "C2", "statement": "U 酉 ⟺ T 可逆",
         "status": "theorem",
         "literature": "Anton_Colbrook_EDMD: isometry vs unitary distinction"},
        {"id": "C3", "statement": "等距的谱在单位圆上 ⟹ 无衰减谱只需保测性",
         "status": "theorem",
         "literature": "Colbrook (2021): unitary extension 存在"},
        {"id": "C4", "statement": "不可逆时 L² = H_u ⊕ H_s（Wold 分解）",
         "status": "theorem",
         "literature": "Anton_Colbrook_EDMD: Wold decomposition"},
    ],
    "manuscript_implication": {
        "current": "Koopman operator of a measure-preserving system is unitary",
        "should_be": "is an isometry (unitary when the map is also invertible)",
        "benefit": "适用范围从可逆保测扩大到全部保测系统",
        "cost": "半天（措辞与引用的修改）",
    },
    "numerical_attempts_failed": [
        "PF/Koopman 混淆",
        "cell-center Ulam 采样破坏等距",
        "误认 dyadic 为 Markov 分划",
        "修正后仍 max|U^T U/N - I| ~ 0.998",
    ],
    "final_numeric": {"N": 1024, "max_dev": 0.99803, "is_isometry": False},
    "recommendation": "引用 Colbrook (2021) 的 unitary extension，不声称独立数值验证",
}

print("=" * 100)
print("方向 C：最终结论")
print("=" * 100)
for p in CONCLUSIONS["propositions"]:
    print(f"\n  【{p['id']}】{p['statement']}")
    print(f"        状态: {p['status']}")
    print(f"        依据: {p['literature']}")
print()
print("=" * 100)
print("对稿件的含义")
print("=" * 100)
mi = CONCLUSIONS["manuscript_implication"]
print(f"  现表述: \"{mi['current']}\"")
print(f"  应改为: \"{mi['should_be']}\"")
print(f"  收益  : {mi['benefit']}")
print(f"  代价  : {mi['cost']}")
print()
print("=" * 100)
print("数值验证：失败")
print("=" * 100)
for i, f in enumerate(CONCLUSIONS["numerical_attempts_failed"], 1):
    print(f"  {i}. {f}")
print(f"\n  最终数值: N={CONCLUSIONS['final_numeric']['N']}, "
      f"max_dev={CONCLUSIONS['final_numeric']['max_dev']}, "
      f"is_isometry={CONCLUSIONS['final_numeric']['is_isometry']}")
print(f"\n  建议: {CONCLUSIONS['recommendation']}")

json.dump(CONCLUSIONS, io.open(OUT, "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
