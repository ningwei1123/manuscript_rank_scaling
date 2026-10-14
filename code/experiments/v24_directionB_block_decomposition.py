# -*- coding: utf-8 -*-
"""方向 B：不对齐时的显式修正界（主角度 / CS 分解）。

推导
====
设 C = 输入协方差（对称半正定，n×n），A = 线性算子，C_y = A C A^T。
取 C 的前 r 个特征子空间 U_r（正交基 P = n×r），Q = I - P P^T。

可达误差 = T_out(r) = sum_{k>r} lam_k(C_y) = tr((I - Pi_r) C_y)，
其中 Pi_r 是 C_y 的前 r 个特征投影。

上界一（最简，已用）
    T_out(r) <= ||Q A||_2^2 · T_in(r),   T_in(r) = tr(P P^T C)
    （因为 tr(Q C_y Q) <= ||QA||^2 tr(P^T C P)）

上界二（本方向：用 CS 分解 / 主角度）
    记 M = Q A P^T  （尾部 -> 头部 的"泄漏"块，n-r 行 r 列）
        N = Q A Q^T  （尾部 -> 尾部 的块）
        L = P A P^T  （头部 -> 头部 的块）
    精确分解：
        tr(Q C_y Q) = tr(M C_h M^T) + tr(N C_t N^T) + 2 tr(M C_ht N^T)
    其中 C = [[C_h, C_ht], [C_ht^T, C_t]] 分块。
    若 C 分块对角（C_ht = 0）：
        tr(Q C_y Q) = tr(M C_h M^T) + tr(N C_t N^T)
    => 两项都可算，且第一项由**主角度**控制：
        ||M||_2 = ||Q A P^T||_2 = sin(主角度) 型的量

本脚本验证：两种上界的紧度，以及分块对角情形的精确等式。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v24_direction_B.json"


def build(n, alpha, r, misalign, seed=0, blockdiag=True):
    rng = np.random.default_rng(seed)
    lam = np.exp(-alpha * np.arange(1, n + 1))
    C = np.diag(lam)
    Qb, _ = np.linalg.qr(rng.standard_normal((n, n)))
    # 对齐部分：标量 × 正交；不对齐部分：随机
    A = Qb + misalign * rng.standard_normal((n, n)) / np.sqrt(n)
    return lam, C, A


def quantities(lam, A, r):
    n = len(lam)
    C = np.diag(lam)
    Cy = A @ C @ A.T
    w_in = np.sort(lam)[::-1]
    w_out = np.sort(np.linalg.eigvalsh(Cy))[::-1]
    T_in = float(w_in[r:].sum())
    T_out = float(w_out[r:].sum())
    P = np.zeros((n, r)); P[:r, :r] = np.eye(r)
    Qp = np.eye(n) - P @ P.T
    # 上界一
    b1 = float(np.linalg.norm(Qp @ A, 2) ** 2 * T_in)
    # 分块
    M = Qp @ A @ P            # (n, r)
    N = Qp @ A @ Qp           # (n, n)
    L = P.T @ A @ P           # (r, r)
    C_h = P.T @ C @ P
    C_t = Qp @ C @ Qp
    C_ht = P.T @ C @ Qp
    term1 = float(np.trace(M @ C_h @ M.T))
    term2 = float(np.trace(N @ C_t @ N.T))
    term3 = float(2 * np.trace(M @ C_ht @ N.T))
    # 分块对角假设下的两项和
    b2 = term1 + term2
    # 精确：tr(Q C_y Q) 与 T_out 的关系
    trQ = float(np.trace(Qp @ Cy))
    # 主角度：U_r 与 A 的像空间的主角度
    UA = np.linalg.svd(A, compute_uv=True)[0]      # A 的左奇异向量
    sv = np.linalg.svd(P.T @ UA, compute_uv=False)  # 主角度余弦
    sv = np.clip(sv, 0, 1)
    theta_max = float(np.arccos(sv.min())) if len(sv) else 0.0
    return dict(T_in=T_in, T_out=T_out, b1=b1, b2=b2, trQ=trQ,
                term1=term1, term2=term2, term3=term3,
                theta_max=theta_max, rho1=b1 / T_in if T_in > 0 else None)


print("=" * 112)
print("方向 B：不对齐时的修正界（两种上界的紧度）")
print("=" * 112)
print("  构造：C = diag(e^{-alpha k})，A = Q(正交) + misalign × 随机")
print()
n, alpha, r = 60, 0.15, 10
print(f"  n={n}, alpha={alpha}, r={r}")
print(f"  {'mis':>7}{'T_in':>11}{'T_out':>11}{'T_out/T_in':>12}"
      f"{'界1/T_out':>11}{'界2/T_out':>11}{'theta_max':>11}")
rows = []
for mis in (0.0, 0.01, 0.05, 0.1, 0.3, 1.0):
    lam, C, A = build(n, alpha, r, mis, seed=11)
    q = quantities(lam, A, r)
    ratio = q["T_out"] / q["T_in"] if q["T_in"] > 0 else np.nan
    print(f"  {mis:>7.2f}{q['T_in']:>11.4e}{q['T_out']:>11.4e}{ratio:>12.6f}"
          f"{q['b1']/q['T_out']:>11.4f}{q['b2']/q['T_out']:>11.4f}"
          f"{np.degrees(q['theta_max']):>10.2f}°")
    rows.append(dict(mis=mis, **{k: v for k, v in q.items()}))

print()
print("=" * 112)
print("检验①：T_out = tr(Q C_y Q)？  （应为否——T_out 用 C_y 自己的特征投影）")
print("=" * 112)
for row in rows[:3]:
    print(f"  mis={row['mis']:<5} T_out={row['T_out']:.6e}  tr(Q C_y Q)={row['trQ']:.6e}"
          f"  差={row['trQ']-row['T_out']:+.3e}")

print()
print("=" * 112)
print("检验②：分块分解 term1 + term2 + term3 是否等于 tr(Q C_y Q)？")
print("=" * 112)
for row in rows[:4]:
    tot = row["term1"] + row["term2"] + row["term3"]
    print(f"  mis={row['mis']:<5} term1+2+3={tot:.6e}  tr(Q C_y Q)={row['trQ']:.6e}"
          f"  相对差={abs(tot-row['trQ'])/max(abs(row['trQ']),1e-30):.3e}")

print()
print("=" * 112)
print("检验③：C_ht = 0（分块对角）时 term3 是否 = 0？")
print("=" * 112)
print("  （本构造 C = diag(lam)，前 r 个与后 n-r 个特征向量正交 => C_ht = 0）")
for row in rows[:4]:
    print(f"  mis={row['mis']:<5} term3={row['term3']:+.3e}  "
          f"（应 ≈ 0：{'Y' if abs(row['term3'])<1e-9 else 'N'}）")

print()
print("=" * 112)
print("判读")
print("=" * 112)
b1r = [r_["b1"] / r_["T_out"] for r_ in rows]
b2r = [r_["b2"] / r_["T_out"] for r_ in rows]
print(f"  界1（||QA||²·T_in）的紧度: {min(b1r):.3f} .. {max(b1r):.3f}")
print(f"  界2（term1 + term2）的紧度: {min(b2r):.3f} .. {max(b2r):.3f}")
print()
print("""
  · term1 = tr(M C_h M^T) 是**尾部->头部泄漏**的贡献，M = Q A P^T，
    其谱范数由 U_r 与 A 的像空间的**主角度**控制。
  · term2 = tr(N C_t N^T) 是**尾部->尾部**的贡献。
  · 当 C 分块对角（即 U_r 是 C 的特征子空间）时 term3 = 0，
    此时 tr(Q C_y Q) = term1 + term2 是**精确**分解。
  · 但 T_out 用 C_y 自己的特征投影，故 T_out <= tr(Q C_y Q)，
    等号当且仅当 P 也是 C_y 的前 r 个特征子空间。
""")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
