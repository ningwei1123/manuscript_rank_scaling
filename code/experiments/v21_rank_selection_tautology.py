# -*- coding: utf-8 -*-
"""方法论核查：秩选择问题是否本质上已解决？

发现：NAARS 给出的秩 = r_true 恒等，因为 r_true 的**定义**就是
    r_true = min{ r : sum_{k>r} p_k <= eps^2 }
而 NAARS 的组件 B 正是这个式子。**同义反复。**

故必须区分三类问题：
  (P1) 给定**已知**谱，选满足精度的最小秩  -> 定义即答案，无算法空间
  (P2) 给定**训练好的模型**，选最优规模    -> 需验证反馈
  (P3) 在**训练前**、从数据预测秩         -> 需谱-秩-精度关系

本脚本检验：E99 的"成功"是否只是**容差错配**（0.99 能量 ≈ 10% 相对误差）。
"""
import io, json, os
import numpy as np

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
OUT = r"E:\deepseekworkspace\experiments_v12\v21_tautology.json"


def load_specs(fn, kind, n_traj=30):
    if kind == "pde":
        import h5py
        p = os.path.join(PD, fn)
        if not os.path.exists(p):
            return None
        out = []
        with h5py.File(p, "r") as f:
            ten = f["tensor"]
            ntr = ten.shape[0]
            idx = np.linspace(0, ntr - 1, min(n_traj, ntr)).astype(int)
            for i in idx:
                field = np.asarray(ten[int(i)], dtype=np.float64)
                if field.ndim > 2:
                    field = field.reshape(field.shape[0], -1)
                Y = np.nan_to_num(field - field.mean(0, keepdims=True))
                sv = np.linalg.svd(Y, compute_uv=False)
                lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
                if lam.sum() > 0:
                    out.append(lam / lam.sum())
        return out or None
    p = os.path.join(FD, fn)
    if not os.path.exists(p):
        return None
    rows = []
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue
    a = np.array(rows)
    v = np.maximum(a[:, 1], 0) ** 2
    return [v / v.sum()] if v.sum() > 0 else None


print("=" * 108)
print("① E99 的固定阈值对应多少相对误差？")
print("=" * 108)
print(f"  {'系统':>28}{'E99 选中秩':>12}{'该秩的相对误差':>16}{'目标 eps':>10}")
CASES = [("PDEBench Advection b=1.0", "1D_Advection_Sols_beta1.0.hdf5", "pde"),
         ("PDEBench Advection b=4.0", "1D_Advection_Sols_beta4.0.hdf5", "pde"),
         ("PDEBench Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "pde"),
         ("KS L=22 N=32", "figures1_ks_spectrum.txt", "txt"),
         ("Lorenz-96 N=40", "figures1_l96_spectrum.txt", "txt")]
rows = []
for nm, fn, kind in CASES:
    sp = load_specs(fn, kind)
    if not sp:
        continue
    errs, rks = [], []
    for p in sp:
        p = np.sort(p)[::-1]
        c = np.cumsum(p)
        r99 = int(np.searchsorted(c, 0.99) + 1)
        err = float(np.sqrt(max(1 - c[r99 - 1], 0)))
        errs.append(err); rks.append(r99)
    rows.append(dict(system=nm, r99_med=float(np.median(rks)),
                     err_med=float(np.median(errs))))
    print(f"  {nm[:28]:>28}{np.median(rks):>12.0f}{np.median(errs):>16.4f}{0.10:>10.2f}")

print()
print("  => 0.99 能量阈值对应的相对误差约为 0.10（即 eps = 0.1）")
print("     故 E99 在 eps = 0.05/0.02 时必然不足，在 eps = 0.2 时过度——")
print("     这不是方法优劣，而是**容差错配**。")

print()
print("=" * 108)
print("② 同义反复核查：r_true 的定义 vs 能量准则")
print("=" * 108)
print("""
  r_true 的定义：
      r_true = min{ r : sum_{k>r} p_k <= eps^2 }
  任何"计算尾能量并与 eps^2 比较"的方法**自动**等于 r_true。

  => 在「谱已知」的前提下，秩选择问题**没有算法空间**：
     正确答案就是定义本身。E99_eps（0.99 -> 1-eps^2）即最优。

  这解释了为何 NAARS 的比值为 1.00：它是同义反复，而非发现。
""")

print("=" * 108)
print("③ 那么真正有算法空间的问题是什么？")
print("=" * 108)
print("""
  (P1) 谱已知、选满足精度的最小秩     -> **已解决**（定义即答案），无算法空间
  (P2) 模型已训练、选最优规模         -> 需验证反馈；本稿的宽度分支已证明不可行
  (P3) 训练前、从**有限数据**预测所需秩 -> **有空间**：谱本身是估计量，有偏差与方差
  (P4) 训练前、从**更廉价的数据**预测   -> 有空间：若只需部分数据的谱

  本稿真正能做的是 (P3)：把**有限样本谱估计误差**纳入秩的选择。
  这正是 Abuduweili 定理的采样项所刻画的：
      eps_samp(n,m) 随 n 增长 => 存在有限样本最优秩 n*(m)
  且该最优秩**不等于** r_true（后者假设谱已知）。
""")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
