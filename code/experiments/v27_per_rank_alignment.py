# -*- coding: utf-8 -*-
"""N5 改进：逐-r 的弱对齐条件（反查发现的实质改进点）。

严格条件（已报告）：T_out(r)/T_in(r) 对所有 r 为常数 <=> A = cQ
弱条件（待验证）：对**给定 r**，若 A 近似保持 C 的**前 r 个**特征子空间，则
                  T_out(r) ≈ T_in(r)

验证：构造 A，使其**只**保持前 r 个特征子空间（其余任意混合），
      检查 T_out(r)/T_in(r) 在 r 处是否 ≈ 1，而在其他 r' 处是否偏离。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v27_per_r_alignment.json"


def build_partial(n, alpha, r0, eps, seed=0):
    """A = c*Q_0 + eps*B，其中 Q_0 保持前 r0 个特征子空间。"""
    rng = np.random.default_rng(seed)
    lam = np.exp(-alpha * np.arange(1, n + 1))
    # Q_0：分块正交——前 r0 维用标量缩放，后 n-r0 维任意正交
    Qm = np.zeros((n, n))
    Qm[:r0, :r0] = np.eye(r0)
    Qb, _ = np.linalg.qr(rng.standard_normal((n - r0, n - r0)))
    Qm[r0:, r0:] = Qb
    A = Qm + eps * rng.standard_normal((n, n)) / np.sqrt(n)
    return lam, A


def ratio_at(lam, A, r):
    n = len(lam)
    C = np.diag(lam)
    Cy = A @ C @ A.T
    w_in = np.sort(lam)[::-1]
    w_out = np.sort(np.linalg.eigvalsh(Cy))[::-1]
    T_in = w_in[r:].sum()
    T_out = w_out[r:].sum()
    return float(T_out / T_in) if T_in > 0 else np.nan


print("=" * 112)
print("N5 改进：逐-r 弱对齐条件")
print("=" * 112)
n, alpha, r0 = 80, 0.1, 20
print(f"  构造：A 只保持 C 的**前 {r0} 个**特征子空间，后 {n-r0} 维任意正交")
print(f"        再叠加 eps × 随机扰动")
print()
print(f"  {'eps':>7}" + "".join(f"{'r='+str(r):>11}" for r in (5, 10, 20, 30, 40, 60)))
rows = []
for eps in (0.0, 0.01, 0.05, 0.1, 0.3):
    lam, A = build_partial(n, alpha, r0, eps)
    line = f"  {eps:>7.3f}"
    vals = {}
    for r in (5, 10, 20, 30, 40, 60):
        v = ratio_at(lam, A, r)
        vals[r] = v
        line += f"{v:>11.5f}"
    rows.append(dict(eps=eps, **{f"r{r}": v for r, v in vals.items()}))
    print(line)

print()
print("=" * 112)
print("判读")
print("=" * 112)
target = [row for row in rows if row["eps"] == 0.0]
if target:
    t = target[0]
    print(f"  eps = 0（严格保持前 {r0} 个特征子空间）:")
    for r in (5, 10, 20, 30, 40, 60):
        v = t[f"r{r}"]
        mark = " <== 对齐点" if r == r0 else ""
        print(f"    r={r:<4} T_out/T_in = {v:.6f}{mark}")
print()
print("""  若仅在 r = r0 处比值 = 1，其它 r 偏离，
  则"逐-r 弱条件"成立：**只需前 r 个特征子空间近似不变，即可在该 r 处用输入尾部**。
  这比 A = cQ 弱得多，是实践中可检验的条件。
""")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
