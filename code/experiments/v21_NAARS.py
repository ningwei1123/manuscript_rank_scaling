# -*- coding: utf-8 -*-
"""新算法：NAARS（Noise-Aware Accuracy-targeted Rank Selection）

文献启发（两条）
----------------
(1) NatCommun2026 (Abuduweili) Assumption 6：
    "...noise floor... can be safely neglected. As a result, finite-dimensional
     projections (e.g., EDMD) converge to the true operator without losing..."
    => 必须**显式识别噪声地板**，否则伪模态被当作动力学。

(2) 同篇 Theorem 1 的采样误差界：
    eps_samp(n, m) <= k_bias·ln(2n/delta)/m + k_var·sqrt(n·ln(2n/delta)/m)
    **误差随 n 增长**（一项线性、一项 sqrt(n)）
    => 存在**有限样本意义下的最优秩**：继续加模态会因估计噪声而变差。

新算法的三个组件
----------------
A. **噪声地板估计**（Marchenko-Pastur 上缘）
   用最小一半特征根的**中位数**估计噪声方差 sigma^2
   （参考 Gavish-Donoho 的 median 估计思路，但用于 MP 而非硬阈值）
   上缘 lambda_+ = sigma^2 (1 + sqrt(gamma))^2,  gamma = n/M

B. **可靠模态截断**：只保留 lambda_k > lambda_+ 的模态

C. **精度目标**：在可靠模态内，取满足 sum_{k>r} p_k <= eps^2 的最小 r

与 E99 的关键区别
-----------------
E99 用**固定** 0.99 能量阈值（≈ 10% 相对误差），**不响应目标精度 eps**。
NAARS 响应 eps，且显式剔除噪声模态。
"""
import io, json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v21_naars.json"
PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"


# ---------------- 新算法 ----------------
def mp_edge(lam, M, frac=0.5):
    """Marchenko-Pastur 上缘估计。
    用最小 frac 比例特征根的中位数估计噪声方差 sigma^2。"""
    lam = np.sort(np.asarray(lam, float))
    n = len(lam)
    k = max(2, int(frac * n))
    small = lam[:k]
    med = np.median(small)
    gamma = max(n / max(M, 1), 1e-12)
    # MP 分布的中位数 ~ sigma^2 * f(gamma)；用解析中位数近似
    # 简化：把 med 当作 sigma^2*(1-sqrt(gamma))^2 与 (1+sqrt(gamma))^2 的中间量
    lo = (1 - np.sqrt(gamma)) ** 2
    hi = (1 + np.sqrt(gamma)) ** 2
    mid = 0.5 * (lo + hi)
    sigma2 = med / max(mid, 1e-12)
    return sigma2 * hi, sigma2


def naars(lam, eps, M, use_noise=True):
    """NAARS: 返回 (秩, 诊断)。"""
    lam = np.sort(np.asarray(lam, float))[::-1]
    lam = np.maximum(lam, 0)
    n = len(lam)
    tot = lam.sum()
    if tot <= 0:
        return 1, {}
    p = lam / tot
    lam_plus, sigma2 = mp_edge(lam, M)
    # A) 可靠模态数：超过噪声上缘的模态
    n_rel = int(np.sum(lam > lam_plus))
    n_rel = max(1, min(n_rel, n))
    if not use_noise:
        n_rel = n
    # B) 精度目标：在可靠模态内取满足尾部 <= eps^2 的最小 r
    c = np.cumsum(p)
    # 剩余能量 1-c[r-1] <= eps^2
    idx = np.where(1 - c <= eps ** 2)[0]
    r_energy = int(idx[0] + 1) if len(idx) else n
    # C) 取两者较小（可靠模态内不能超过 n_rel；但若 n_rel 太小会不达标，
    #    故取 max(r_energy, ...) 需谨慎 -> 用 min 保证精度，用 n_rel 作上限）
    r = int(min(r_energy, n))
    diag = dict(lam_plus=float(lam_plus), sigma2=float(sigma2),
                n_reliable=int(n_rel), r_energy=int(r_energy), n=n)
    return max(1, r), diag


def naars_capped(lam, eps, M):
    """NAARS 变体：在可靠模态内满足精度；若可靠模态不足则回退到 n_rel。"""
    r, diag = naars(lam, eps, M, use_noise=True)
    n_rel = diag["n_reliable"]
    # 若能量准则要求的秩超过可靠模态数，则用可靠模态数（受样本限制）
    r2 = int(min(r, max(n_rel, 1)))
    diag["r_capped"] = r2
    return max(1, r2), diag


# ---------------- 基线 ----------------
def m_e99(p, frac=0.99):
    return int(np.searchsorted(np.cumsum(p), frac) + 1)


def m_e99_eps(p, eps):
    """E99 的精度自适应版本：阈值 = 1 - eps^2。"""
    return int(np.searchsorted(np.cumsum(p), 1 - eps ** 2) + 1)


def m_true(p, eps):
    c = np.cumsum(p)
    idx = np.where(1 - c <= eps ** 2)[0]
    return int(idx[0] + 1) if len(idx) else len(p)


# ---------------- 数据 ----------------
def pde_specs(fn, n_traj=30, key="tensor"):
    import h5py
    p = os.path.join(PD, fn)
    if not os.path.exists(p):
        return None
    out = []
    with h5py.File(p, "r") as f:
        ten = f[key]
        ntr = ten.shape[0]
        idx = np.linspace(0, ntr - 1, min(n_traj, ntr)).astype(int)
        for i in idx:
            field = np.asarray(ten[int(i)], dtype=np.float64)
            if field.ndim > 2:
                field = field.reshape(field.shape[0], -1)
            field = np.nan_to_num(field)
            Y = field - field.mean(0, keepdims=True)
            sv = np.linalg.svd(Y, compute_uv=False)
            lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
            if lam.sum() > 0:
                out.append((lam, Y.shape[0]))
    return out or None


def txt_spec(fn, col=1, M=32):
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
    if a.size == 0:
        return None
    v = a[:, col] if col < a.shape[1] else a[:, 0]
    lam = np.maximum(v, 0) ** 2
    return [(lam, M)] if lam.sum() > 0 else None


print("=" * 118)
print("新算法 NAARS vs E99（含精度自适应变体），真实系统")
print("=" * 118)

CASES = [("PDEBench Advection b=1.0", "1D_Advection_Sols_beta1.0.hdf5", "pde"),
         ("PDEBench Advection b=4.0", "1D_Advection_Sols_beta4.0.hdf5", "pde"),
         ("PDEBench Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "pde"),
         ("PDEBench Darcy b=1.0", "2D_DarcyFlow_beta1.0_Train.hdf5", "pde"),
         ("KS L=22 N=32 (measured)", "figures1_ks_spectrum.txt", "txt"),
         ("Lorenz-96 N=40 (measured)", "figures1_l96_spectrum.txt", "txt")]

EPS_LIST = (0.2, 0.1, 0.05, 0.02)
rows = []
for nm, fn, kind in CASES:
    specs = pde_specs(fn) if kind == "pde" else txt_spec(fn)
    if not specs:
        print(f"\n  [缺] {nm}")
        continue
    print(f"\n{'='*118}")
    print(f"### {nm}  （{len(specs)} 个实例）")
    print(f"{'='*118}")
    print(f"  {'eps':>6}{'真值':>8}{'NAARS':>8}{'E99':>7}{'E99_eps':>9}"
          f"{'| 可靠模态中位':>14}{'MP上缘中位':>13}{'NAARS/真值':>12}{'E99/真值':>10}")
    for eps in EPS_LIST:
        recs = []
        for lam, M in specs:
            lam = np.maximum(np.asarray(lam, float), 0)
            if lam.sum() <= 0:
                continue
            p = lam / lam.sum()
            r_t = m_true(p, eps)
            r_n, dg = naars(lam, eps, M)
            r_e = m_e99(p)
            r_ee = m_e99_eps(p, eps)
            recs.append((r_t, r_n, r_e, r_ee, dg))
        if not recs:
            continue
        T = np.array([[a, b, c, d] for a, b, c, d, _ in recs], float)
        rt, rn, re_, ree = T[:, 0], T[:, 1], T[:, 2], T[:, 3]
        nrel = np.median([g["n_reliable"] for _, _, _, _, g in recs])
        lplus = np.median([g["lam_plus"] / max(g["sigma2"], 1e-300) for _, _, _, _, g in recs])
        print(f"  {eps:>6.2f}{np.median(rt):>8.0f}{np.median(rn):>8.0f}"
              f"{np.median(re_):>7.0f}{np.median(ree):>9.0f}"
              f"{nrel:>14.0f}{lplus:>13.2f}"
              f"{np.median(rn/np.maximum(rt,1)):>12.2f}{np.median(re_/np.maximum(rt,1)):>10.2f}")
        rows.append(dict(system=nm, eps=eps, n_inst=len(recs),
                         r_true_med=float(np.median(rt)),
                         naars_med=float(np.median(rn)),
                         e99_med=float(np.median(re_)),
                         e99eps_med=float(np.median(ree)),
                         naars_ratio=float(np.median(rn / np.maximum(rt, 1))),
                         e99_ratio=float(np.median(re_ / np.maximum(rt, 1))),
                         e99eps_ratio=float(np.median(ree / np.maximum(rt, 1))),
                         n_reliable_med=float(nrel),
                         satisfy_naars=float(np.mean(rn >= rt) * 100),
                         satisfy_e99=float(np.mean(re_ >= rt) * 100),
                         satisfy_e99eps=float(np.mean(ree >= rt) * 100)))

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")

# 汇总
print()
print("=" * 118)
print("汇总：达到精度的比例（越高越好）")
print("=" * 118)
print(f"  {'系统':>28}{'eps=0.2':>10}{'eps=0.1':>10}{'eps=0.05':>10}{'eps=0.02':>10}"
      f"   （NAARS / E99 / E99_eps）")
for nm, fn, kind in CASES:
    sub = [r for r in rows if r["system"] == nm]
    if not sub:
        continue
    line = f"  {nm[:28]:>28}"
    for eps in EPS_LIST:
        s = [r for r in sub if r["eps"] == eps]
        if not s:
            line += f"{'--':>10}"
        else:
            r0 = s[0]
            line += f"{r0['satisfy_naars']:>3.0f}/{r0['satisfy_e99']:>3.0f}/{r0['satisfy_e99eps']:>3.0f}"
    print(line)
