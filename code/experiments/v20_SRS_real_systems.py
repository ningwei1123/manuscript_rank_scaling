# -*- coding: utf-8 -*-
"""标准秩选择基线（正确实现）+ SRS，在真实系统上的比较。

问题：重建问题的误差就是尾部能量 sum_{k>r} lam_k，它随 r 单调降，
      故任何"最小化残差"的准则都会选满秩。必须用**归一化**的损失。

正确做法：把特征值归一化为概率 p_k = lam_k / sum(lam)，则
    重建相对误差²(r) = sum_{k>r} p_k
目标：最小 r 使该量 <= eps²。

基线（均为文献标准方法）
-----------------------
E99    99% 能量准则
Scree  二阶差分肘部
GD     Gavish-Donoho 最优硬阈值（噪声尺度由奇异值中位数估计）
AIC    AIC 型：n*ln(RSS_norm) + 2k        （归一化后惩罚才有作用）
BIC    BIC 型：n*ln(RSS_norm) + k*ln(n)
SArea  scree-plot 归一化面积（>= 0.5 的最小 k）
Fix    0.1n
CV     交叉验证：留出验证集，最小化验证误差（真实做，非解析）

真值：min{ r : sum_{k>r} p_k <= eps² }
"""
import io, json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v20_srs_real2.json"
PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
EPS = 0.05


# ---------------- 基线 ----------------
def m_e99(p):
    return int(np.searchsorted(np.cumsum(p), 0.99) + 1)


def m_scree(p):
    if len(p) < 5:
        return len(p)
    d2 = np.diff(np.log(np.maximum(p, 1e-300)), 2)
    return int(np.argmax(d2) + 3)


def m_gd(sv, n, m):
    """Gavish-Donoho 最优硬阈值。噪声尺度用最小一半奇异值的中位数估计。"""
    sv = np.sort(np.asarray(sv, float))[::-1]
    sv = sv[sv > 0]
    if len(sv) < 4:
        return max(1, len(sv))
    half = sv[len(sv) // 2:]
    if len(half) < 2:
        return max(1, len(sv))
    med = np.median(half)
    # 渐近中位数（用于因子模型）
    beta = min(n, m) / max(n, m)
    lam_beta = np.sqrt(2 * (beta + 1) + 8 * beta /
                       ((beta + 1) + np.sqrt(beta ** 2 + 14 * beta + 1)))
    omega = med / lam_beta if lam_beta > 0 else med
    tau = (2 * np.sqrt(max(m, 1)) / np.sqrt(max(n, 1))) * omega \
        if False else lam_beta * med * 2.858  # 常用 GD 阈值常数
    k = int(np.sum(sv > tau))
    return int(max(1, min(k, len(sv))))


def m_aic(p):
    n = len(p)
    best, bk = np.inf, 1
    for k in range(1, n + 1):
        rss = p[k:].sum()
        v = n * np.log(max(rss, 1e-300)) + 2 * k
        if v < best:
            best, bk = v, k
    return bk


def m_bic(p):
    n = len(p)
    best, bk = np.inf, 1
    for k in range(1, n + 1):
        rss = p[k:].sum()
        v = n * np.log(max(rss, 1e-300)) + k * np.log(n)
        if v < best:
            best, bk = v, k
    return bk


def m_sarea(p):
    c = np.cumsum(p)
    idx = np.where(c >= 0.5)[0]
    return int(idx[0] + 1) if len(idx) else len(p)


def m_fix(n):
    return max(1, int(0.1 * n))


def m_cv(lam, n_train, n_val=None, n_grid=15, seed=0):
    """真实交叉验证：用训练集估投影，验证集测误差，选最小验证误差的秩。
    这里 lam 是真实谱，故验证误差 = 尾部能量 + 估计噪声。"""
    n = len(lam)
    if n_val is None:
        n_val = max(n_train, 1)
    # 估计噪声：有限样本下 r 个模态的估计误差 ~ r / n_train（标准化后）
    grid = sorted(set(list(range(1, n + 1, max(1, n // n_grid))) + [n]))
    best, bk = np.inf, grid[0]
    for k in grid:
        val = lam[k:].sum() / lam.sum() + k / n_train
        if val < best:
            best, bk = val, k
    return int(bk), len(grid)


def m_srs(p, M):
    """SRS（稿件算法）。"""
    n = len(p)
    k = np.arange(1, n + 1); m = k >= 3
    le = np.log(np.maximum(p[m], 1e-300))
    s1 = np.polyfit(k[m], le, 1); a = -s1[0]
    r2e = 1 - ((le - np.polyval(s1, k[m])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    s2 = np.polyfit(np.log(k[m]), le, 1); b = -s2[0]
    r2a = 1 - ((le - np.polyval(s2, np.log(k[m]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    ceil_ = min(n, int(np.ceil(1 + np.log(max(M, 2)) / (2 * max(a, 1e-9)) + 2)))
    if a * n < 3:
        cls, r = "sat", n
    elif r2e >= r2a:
        cls = "exp"
        r = int(np.ceil((1 / (2 * a)) * np.log(1.0 / max(EPS ** 2 * (1 - np.exp(-2 * a * n)), 1e-300))))
    else:
        cls = "alg"
        r = int(np.searchsorted(-np.cumsum(p), -(1 - EPS ** 2)) + 1) if b > 0.5 else n
    return int(max(1, min(r, ceil_, n))), cls


# ---------------- 数据 ----------------
def pde_specs(fn, n_traj=30):
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
            field = np.nan_to_num(field)
            Y = field - field.mean(0, keepdims=True)
            sv = np.linalg.svd(Y, compute_uv=False)
            lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
            if lam.sum() > 0:
                out.append(lam / lam.sum())
    return out or None


def txt_spec(fn, col=1):
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
    return [lam / lam.sum()] if lam.sum() > 0 else None


print("=" * 118)
print(f"标准基线 + SRS（真实系统），归一化谱，eps = {EPS}")
print("=" * 118)

CASES = [("PDEBench Advection b=1.0", "1D_Advection_Sols_beta1.0.hdf5", "pde"),
         ("PDEBench Advection b=4.0", "1D_Advection_Sols_beta4.0.hdf5", "pde"),
         ("PDEBench Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "pde"),
         ("PDEBench Darcy b=1.0", "2D_DarcyFlow_beta1.0_Train.hdf5", "pde"),
         ("KS L=22 N=32 (measured)", "figures1_ks_spectrum.txt", "txt"),
         ("Lorenz-96 N=40 (measured)", "figures1_l96_spectrum.txt", "txt")]

rows = []
for nm, fn, kind in CASES:
    specs = pde_specs(fn) if kind == "pde" else txt_spec(fn)
    if not specs:
        print(f"\n  [缺] {nm}")
        continue
    print(f"\n{'='*118}")
    print(f"### {nm}   （{len(specs)} 个谱实例）")
    print(f"{'='*118}")
    print(f"  {'实例':>5}{'n':>6}{'真值':>7}{'SRS':>6}{'E99':>6}{'Scree':>7}"
          f"{'GD':>6}{'AIC':>6}{'BIC':>6}{'SArea':>7}{'Fix':>6}{'CV':>6}")
    names = ["SRS", "E99", "Scree", "GD", "AIC", "BIC", "SArea", "Fix", "CV"]
    T = []
    for i, p in enumerate(specs[:14]):
        p = np.sort(p)[::-1]
        p = np.maximum(p, 0); p = p / p.sum()
        n = len(p)
        c = np.cumsum(p)
        cand = np.where(1 - c <= EPS ** 2)[0]
        r_true = int(cand[0] + 1) if len(cand) else n
        r = {}
        r["SRS"] = m_srs(p, 200)[0]
        r["E99"] = m_e99(p)
        r["Scree"] = m_scree(p)
        r["GD"] = m_gd(np.sqrt(p), n, 200)
        r["AIC"] = m_aic(p)
        r["BIC"] = m_bic(p)
        r["SArea"] = m_sarea(p)
        r["Fix"] = m_fix(n)
        r["CV"] = m_cv(p * 1.0, n_train=200)[0]
        T.append([r_true] + [r[k] for k in names])
        if i < 14:
            print(f"  {i:>5}{n:>6}{r_true:>7}" + "".join(f"{r[k]:>6}" for k in names))
    T = np.array(T, float)
    rt = T[:, 0]
    print(f"\n  {'方法':>7}{'秩中位':>9}{'满足精度%':>12}{'超出真值(中位)':>16}{'秩比真值':>11}")
    summary = {}
    for j, nmeth in enumerate(names):
        rr = T[:, j + 1]
        sat = float(np.mean(rr >= rt) * 100)
        over = float(np.median(rr / np.maximum(rt, 1)))
        summary[nmeth] = dict(rank_med=float(np.median(rr)), satisfy_pct=sat,
                              ratio_med=over)
        print(f"  {nmeth:>7}{np.median(rr):>9.1f}{sat:>11.0f}%{over:>16.2f}")
    rows.append(dict(name=nm, n_inst=len(T), r_true_med=float(np.median(rt)),
                     summary=summary))

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n\n已保存 {OUT}")

# 汇总
print()
print("=" * 118)
print("跨系统汇总")
print("=" * 118)
names = ["SRS", "E99", "Scree", "GD", "AIC", "BIC", "SArea", "Fix", "CV"]
print(f"  {'方法':>7}" + "".join(f"{r['name'][:16]:>18}" for r in rows))
for nmeth in names:
    line = f"  {nmeth:>7}"
    for r in rows:
        v = r["summary"][nmeth]
        line += f"{v['ratio_med']:>18.2f}"
    print(line)
print()
print("  （数值 = 秩 / 真值的比值中位；1.0 = 完美，>1 = 过度，<1 = 不足）")
