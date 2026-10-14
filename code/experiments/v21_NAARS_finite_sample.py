# -*- coding: utf-8 -*-
"""NAARS-FS：有限样本感知的秩选择（唯一有算法空间的版本）

论点
----
在「谱已精确已知」时，秩选择无算法空间（正确答案 = 定义）。
但当谱是**从 M 个样本估计**的，存在两个效应：
  (1) 样本不足时，高阶特征根被**高估**（Wishart 涨落）-> 假信号
  (2) 样本不足时，低位特征根被**压缩** -> 谱形失真
故「用估计谱算出的尾能量」有系统性偏差，而 **M 相关的最优秩** 偏离 r_true。

文献依据（Abuduweili 2026, Theorem 1）
    eps(n,m) <= k_b·ln(2n/d)/m + k_v·sqrt(n ln(2n/d)/m) + C·n^{-(a-1/2)}
                 ______ 采样误差（随 n 增长）______/        __ 投影误差（随 n 下降）__/
    => 存在有限样本最优 n*(m)；n*(m) < r_true 当 M 不足。

NAARS-FS 的做法
----------------
1. 估计噪声尺度 sigma^2（用最小一半特征根的中位数 + MP 修正）
2. MP 上缘 lam_+ = sigma^2 (1+sqrt(gamma))^2, gamma = n/M
3. **偏差修正**：对 lam_k <= lam_+ 的模态视为噪声，从尾部能量中剔除
   （即"不可信模态不计入可达误差"）
4. 在**可信模态**内选满足 eps^2 的最小 r

对照：E99_eps（不区分可信/不可信，直接用估计谱）
评价：在**每个 M** 上，用**真谱**（大 M 极限）算 r_true 作真值。
"""
import io, json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v21_naars_fs.json"
PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"


def true_spectrum(fn, kind, n_traj=30):
    """大样本谱（用作真值）：用全部可用快照估计。"""
    if kind == "pde":
        import h5py
        p = os.path.join(PD, fn)
        if not os.path.exists(p):
            return None
        with h5py.File(p, "r") as f:
            ten = f["tensor"]
            i = int(ten.shape[0] // 2)
            field = np.asarray(ten[i], dtype=np.float64)
            if field.ndim > 2:
                field = field.reshape(field.shape[0], -1)
            Y = np.nan_to_num(field - field.mean(0, keepdims=True))
            sv = np.linalg.svd(Y, compute_uv=False)
            return (sv ** 2) / max(Y.shape[0] - 1, 1)
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
    return np.maximum(a[:, 1], 0) ** 2


def sample_spectrum(lam_full, n_state, M, seed):
    """从真谱抽样：生成 X (M x n_state)，其特征根即样本谱。"""
    rng = np.random.default_rng(seed)
    n = min(n_state, len(lam_full))
    lam = np.maximum(lam_full[:n], 0)
    X = rng.standard_normal((M, n)) * np.sqrt(lam)[None, :]
    Y = X - X.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / max(M - 1, 1)


def r_true_from(lam, eps):
    lam = np.sort(np.maximum(lam, 0))[::-1]
    tot = lam.sum()
    if tot <= 0:
        return 1
    c = np.cumsum(lam) / tot
    idx = np.where(1 - c <= eps ** 2)[0]
    return int(idx[0] + 1) if len(idx) else len(lam)


def mp_edge(lam, M, frac=0.5):
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))
    n = len(lam)
    k = max(2, int(frac * n))
    med = np.median(lam[:k])
    gamma = max(n / max(M, 1), 1e-12)
    lo = (1 - np.sqrt(gamma)) ** 2
    hi = (1 + np.sqrt(gamma)) ** 2
    mid = 0.5 * (lo + hi)
    sigma2 = med / max(mid, 1e-12)
    return sigma2 * hi, sigma2


def e99_eps(lam, eps):
    return r_true_from(lam, eps)


def naars_fs(lam, eps, M, frac=0.35):
    """有限样本感知：剔除低于 MP 上缘的模态，再在可信模态内选秩。"""
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    n = len(lam)
    tot = lam.sum()
    if tot <= 0:
        return 1, {}
    lam_plus, sigma2 = mp_edge(lam, M)
    reliable = lam > lam_plus
    n_rel = int(reliable.sum())
    if n_rel < 1:
        # 全部视为噪声：退回能量准则
        return r_true_from(lam, eps), dict(n_reliable=0, lam_plus=float(lam_plus))
    # 在可信模态内：可解释能量 = 可信模态之和；不可信模态不计入分子也不计入分母
    lam_trunc = np.where(reliable, lam, 0.0)
    tot_tr = lam_trunc.sum()
    c = np.cumsum(lam_trunc) / max(tot_tr, 1e-300)
    idx = np.where(1 - c <= eps ** 2)[0]
    r = int(idx[0] + 1) if len(idx) else n_rel
    return int(max(1, min(r, n_rel))), dict(n_reliable=n_rel,
                                            lam_plus=float(lam_plus),
                                            sigma2=float(sigma2))


print("=" * 116)
print("NAARS-FS（有限样本感知）vs E99_eps，沿样本量 M 扫描")
print("=" * 116)
print("  真值 = 用大样本谱算出的 r_true；方法 = 用 M 个样本的估计谱")

CASES = [("PDEBench Advection b=1", "1D_Advection_Sols_beta1.0.hdf5", "pde"),
         ("PDEBench Advection b=4", "1D_Advection_Sols_beta4.0.hdf5", "pde"),
         ("PDEBench Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "pde"),
         ("KS L=22 N=32", "figures1_ks_spectrum.txt", "txt"),
         ("Lorenz-96 N=40", "figures1_l96_spectrum.txt", "txt")]
EPS = 0.05
MS = (30, 60, 120, 300, 1000, 4000)
rows = []
for nm, fn, kind in CASES:
    full = true_spectrum(fn, kind)
    if full is None or full.sum() <= 0:
        print(f"\n  [缺] {nm}")
        continue
    n_state = len(full)
    rt = r_true_from(full, EPS)
    print(f"\n{'='*116}")
    print(f"### {nm}   n={n_state}   r_true(eps={EPS}) = {rt}")
    print(f"{'='*116}")
    print(f"  {'M':>7}{'E99_eps':>10}{'比值':>8}{'NAARS-FS':>10}{'比值':>8}"
          f"{'可靠模态':>10}{'满足率 E99':>12}{'满足率 NAARS':>14}")
    for M in MS:
        if M < 5:
            continue
        re_, rn, nr = [], [], []
        for sd in range(12):
            ls = sample_spectrum(full, n_state, M, 1000 + sd)
            re_.append(e99_eps(ls, EPS))
            rr, dg = naars_fs(ls, EPS, M)
            rn.append(rr); nr.append(dg["n_reliable"])
        re_ = np.array(re_, float); rn = np.array(rn, float)
        print(f"  {M:>7}{np.median(re_):>10.0f}{np.median(re_/max(rt,1)):>8.2f}"
              f"{np.median(rn):>10.0f}{np.median(rn/max(rt,1)):>8.2f}"
              f"{np.median(nr):>10.0f}"
              f"{np.mean(re_>=rt)*100:>11.0f}%{np.mean(rn>=rt)*100:>13.0f}%")
        rows.append(dict(system=nm, M=M, r_true=rt,
                         e99_med=float(np.median(re_)),
                         naars_med=float(np.median(rn)),
                         e99_ratio=float(np.median(re_ / max(rt, 1))),
                         naars_ratio=float(np.median(rn / max(rt, 1))),
                         n_rel_med=float(np.median(nr)),
                         e99_sat=float(np.mean(re_ >= rt) * 100),
                         naars_sat=float(np.mean(rn >= rt) * 100)))

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")

print()
print("=" * 116)
print("汇总：满足精度的比例（越高越好），按 M 平均")
print("=" * 116)
print(f"  {'系统':>28}" + "".join(f"{'M='+str(M):>11}" for M in MS))
for nm, fn, kind in CASES:
    sub = [r for r in rows if r["system"] == nm]
    if not sub:
        continue
    line = f"  {nm[:28]:>28}"
    for M in MS:
        s = [r for r in sub if r["M"] == M]
        line += f"{s[0]['e99_sat']:>5.0f}/{s[0]['naars_sat']:<5.0f}" if s else f"{'--':>11}"
    print(line)
print()
print("  （格式：E99_eps满足率 / NAARS-FS满足率）")
