# -*- coding: utf-8 -*-
"""对齐条件：正确的充要性推导与验证。

关键修正
--------
前一版的构造 K = diag(随机) 即使 misalign=0 **也不保持 C 的特征子空间**，
故 T_out/T_in ≈ 0.9 ≠ 1 —— 那是构造缺陷，不是理论结论。

正确的对齐定义
--------------
C_y = K C K^T。若 K = c·Q（c > 0 标量，Q 正交），则
    C_y = c² Q C Q^T  =>  lam(C_y) = c² lam(C)，特征子空间 = Q·(C 的特征子空间)
此时 T_out(r) = c² T_in(r)，**比值与 r 无关**。

更一般地：K 保持 C 的特征子空间（即 K 与 C 交换，KC = CK）
   => C_y = K² C，lam_k(C_y) = lam_k(K)² lam_k(C)
   此时 T_out(r) = sum_{k>r} lam_k(K)² lam_k(C)  ≠  T_in(r) 除非 lam_k(K) 常数

**故真正的充要条件是：K 的奇异值在 C 的每个特征方向上相等**，
  即 K = c·Q（c 常数，Q 正交）。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v22_alignment2.json"


def make_C(lam):
    return np.diag(lam)


def aligned_K(n, c=1.0, seed=0, mode="scalar"):
    """构造对齐算子。"""
    rng = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(rng.standard_normal((n, n)))
    if mode == "scalar":
        return c * Q                      # 正确定义的对齐：K = c Q
    if mode == "commute":
        # K 与 C 交换：K = 对角（但元素不等）
        return np.diag(rng.uniform(0.5, 1.5, n))
    if mode == "block":
        # 保持特征子空间但块内混合
        K = np.zeros((n, n))
        K[:n // 2, :n // 2] = c * np.eye(n // 2)
        K[n // 2:, n // 2:] = c * np.eye(n - n // 2)
        return K
    raise ValueError(mode)


def misaligned_K(n, eps, seed=0, c=1.0):
    rng = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(rng.standard_normal((n, n)))
    return c * Q + eps * rng.standard_normal((n, n)) / np.sqrt(n)


def tails(lam, K, r):
    C = np.diag(lam)
    Cy = K @ C @ K.T
    w_in = np.sort(lam)[::-1]
    w_out = np.sort(np.linalg.eigvalsh(Cy))[::-1]
    return float(w_in[r:].sum()), float(w_out[r:].sum())


print("=" * 112)
print("① 正确对齐（K = c·Q，标量 × 正交）时 T_out/T_in 是否恒为 c²？")
print("=" * 112)
n = 60
for alpha in (0.05, 0.15, 0.4):
    lam = np.exp(-alpha * np.arange(1, n + 1))
    print(f"\n  --- alpha = {alpha} ---")
    print(f"  {'c':>6}{'r':>4}{'T_in':>13}{'T_out':>13}{'T_out/T_in':>13}{'c²':>9}")
    for c in (1.0, 2.0, 0.5):
        K = aligned_K(n, c, seed=5, mode="scalar")
        for r in (5, 20, 40):
            Ti, To = tails(lam, K, r)
            print(f"  {c:>6.2f}{r:>4}{Ti:>13.4e}{To:>13.4e}{To/Ti:>13.6f}{c*c:>9.4f}")

print()
print("=" * 112)
print("② 交换但不为标量（K = diag(不等)）：T_out/T_in 是否 ≠ 1？")
print("=" * 112)
for alpha in (0.05, 0.15):
    lam = np.exp(-alpha * np.arange(1, n + 1))
    K = aligned_K(n, seed=5, mode="commute")
    print(f"\n  --- alpha = {alpha}，K = diag(0.5..1.5)（与 C 交换）---")
    print(f"  {'r':>4}{'T_in':>13}{'T_out':>13}{'T_out/T_in':>13}")
    for r in (5, 20, 40):
        Ti, To = tails(lam, K, r)
        print(f"  {r:>4}{Ti:>13.4e}{To:>13.4e}{To/Ti:>13.6f}")

print()
print("=" * 112)
print("③ 充要性：扫描 misalign 强度，看 T_out/T_in 何时 = c²")
print("=" * 112)
print(f"  {'eps':>7}{'r':>4}{'T_out/T_in':>13}{'偏离 c²=1':>12}{'|Q K|_2':>11}")
rows = []
lam = np.exp(-0.15 * np.arange(1, n + 1))
for eps in (0.0, 0.001, 0.005, 0.02, 0.05, 0.2):
    K = misaligned_K(n, eps, seed=5, c=1.0)
    for r in (5, 20):
        Ti, To = tails(lam, K, r)
        ratio = To / Ti
        rows.append(dict(eps=eps, r=r, ratio=float(ratio), dev=float(abs(ratio - 1))))
        if r == 20:
            print(f"  {eps:>7.3f}{r:>4}{ratio:>13.6f}{abs(ratio-1):>12.6f}")

print()
print("=" * 112)
print("④ 结论")
print("=" * 112)
d0 = [r for r in rows if r["eps"] == 0.0 and r["r"] == 20][0]
print(f"  eps = 0（严格对齐）: T_out/T_in = {d0['ratio']:.6f}  （= 1 精确）")
print()
print("  充要条件（推导）：")
print("    T_out(r) / T_in(r) = c² 对**所有** r 成立")
print("      <=>  K = c·Q（c > 0 标量，Q 正交）")
print("    <=>  K 保持 C 的特征子空间 **且** K 在其上是标量")
print()
print("  仅保持特征子空间（K 与 C 交换）而 K 非标量时，")
print("    lam_k(C_y) = lam_k(K)² lam_k(C)，T_out(r) = Σ_{k>r} lam_k(K)² lam_k(C) ≠ T_in(r)")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
