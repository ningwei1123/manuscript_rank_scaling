# -*- coding: utf-8 -*-
"""修正的 PDEBench Advection 分析。

关键修正：
  1. **单一轨迹假设**：论文的协方差 C 是**单一轨迹**上的时间平均。
     PDEBench 的 tensor 是 (n_traj, n_t, n_x)，每个轨迹有**不同初值**，
     把它们混在一起会引入初值系综的方差（主导谱），掩盖时间协方差。
     -> 必须**逐轨迹**计算，再汇总。
  2. **状态维数**：单一轨迹在时刻 t 的状态是 1024 维空间场；
     协方差应在**跨时间**上估计，得到 1024x1024 矩阵（而非 205,824 特征）。
"""
import io, json, os
import numpy as np
import h5py

D = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
OUT = r"E:\deepseekworkspace\experiments_v12\v15_pdebench_advection.json"


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]
    e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def classify(lam, eps_lo=0.3, eps_hi=1e-4):
    lam = np.sort(lam)[::-1]; n = len(lam); k = np.arange(1, n + 1)
    pos = lam > 1e-16
    le = np.log(lam[pos])
    se = np.polyfit(k[pos], le, 1)
    r2e = 1 - ((le - np.polyval(se, k[pos])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    sa = np.polyfit(np.log(k[pos]), le, 1)
    r2a = 1 - ((le - np.polyval(sa, np.log(k[pos]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    eps = np.logspace(np.log10(eps_lo), np.log10(eps_hi), 60)
    r = ranks(lam, eps)
    m = r < n * 0.999
    if m.sum() < 8:
        m = np.ones_like(r, bool)
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / ((r[m] - r[m].mean()) ** 2).sum()
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    r2p = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / ((lg - lg.mean()) ** 2).sum()
    sc = "EXP" if r2e > r2a else "ALG"
    rc = "ALG" if r2p > r2l else "EXP"
    return sc, rc, (sc == rc), float(-sa[0]), float(pp[0]), dict(
        r2e=float(r2e), r2a=float(r2a), r2l=float(r2l), r2p=float(r2p),
        rank_1e3=float(ranks(lam, [1e-3])[0]), rank_1e6=float(ranks(lam, [1e-6])[0]))


def cov_from_trajectory(field):
    """field: (n_t, n_x)。返回协方差特征值（跨时间）。"""
    Y = field - field.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / max(Y.shape[0] - 1, 1), sv


p = os.path.join(D, "1D_Advection_Sols_beta1.0.hdf5")
res = {}
print("=" * 100)
print("PDEBench 1D_Advection beta=1.0：逐轨迹分析（单一轨迹假设）")
print("=" * 100)

with h5py.File(p, "r") as f:
    beta_attr = float(f.attrs.get("beta", float("nan")))
    ten = f["tensor"]
    ntr, nt, nx = ten.shape
    print(f"  tensor shape = {ten.shape}  (n_traj={ntr}, n_t={nt}, n_x={nx})")
    print(f"  根属性 beta = {beta_attr}")
    print()

    # 逐轨迹：先取前 30 条，每条用全部 201 个时间步
    N_TRAJ = 30
    print(f"  {'轨迹':>5}{'谱类':>7}{'秩类':>7}{'一致':>6}{'beta_fit':>10}{'秩指数':>9}"
          f"{'rank(1e-3)':>12}{'rank(1e-6)':>12}{'R2log':>8}{'R2pow':>8}")
    agg = []
    for i in range(N_TRAJ):
        field = np.asarray(ten[i], dtype=np.float64)      # (201, 1024)
        lam, sv = cov_from_trajectory(field)
        sc, rc, agree, bfit, rexp, r2d = classify(lam)
        agg.append(dict(traj=int(i), spec=sc, rank=rc, agree=bool(agree),
                        beta_fit=bfit, rank_exp=rexp, **r2d))
        print(f"  {i:>5}{sc:>7}{rc:>7}{'✓' if agree else '✗':>6}{bfit:>10.4f}{rexp:>9.4f}"
              f"{r2d['rank_1e3']:>12.0f}{r2d['rank_1e6']:>12.0f}"
              f"{r2d['r2l']:>8.4f}{r2d['r2p']:>8.4f}")

    ag = sum(a["agree"] for a in agg)
    print(f"\n  一致 {ag}/{len(agg)}")
    print(f"  beta_fit: 中位 {np.median([a['beta_fit'] for a in agg]):.4f}  "
          f"范围 {min(a['beta_fit'] for a in agg):.4f} .. {max(a['beta_fit'] for a in agg):.4f}")
    print(f"  秩指数:  中位 {np.median([a['rank_exp'] for a in agg]):.4f}  "
          f"范围 {min(a['rank_exp'] for a in agg):.4f} .. {max(a['rank_exp'] for a in agg):.4f}")

    res = dict(file="1D_Advection_Sols_beta1.0.hdf5", beta_attr=beta_attr,
               n_traj_total=int(ntr), n_t=int(nt), n_x=int(nx),
               n_traj_used=N_TRAJ, per_trajectory=agg,
               agree_rate=ag / len(agg),
               beta_fit_median=float(np.median([a["beta_fit"] for a in agg])),
               rank_exp_median=float(np.median([a["rank_exp"] for a in agg])),
               spec_classes=dict(EXP=sum(1 for a in agg if a["spec"] == "EXP"),
                                 ALG=sum(1 for a in agg if a["spec"] == "ALG")),
               rank_classes=dict(EXP=sum(1 for a in agg if a["rank"] == "EXP"),
                                 ALG=sum(1 for a in agg if a["rank"] == "ALG")))

json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
