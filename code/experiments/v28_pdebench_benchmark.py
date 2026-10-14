# -*- coding: utf-8 -*-
"""路 B 步骤 1（修正）：加入 Darcy（稳态，空间协方差）。"""
import io, json, os
import numpy as np
import h5py

PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
OUT = r"E:\deepseekworkspace\experiments_v12\v28_pdebench_benchmark.json"
EPS_LIST = (0.20, 0.10, 0.05, 0.02)


def r_true(lam, eps):
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    c = np.cumsum(lam) / max(lam.sum(), 1e-300)
    idx = np.where(1 - c <= eps ** 2)[0]
    return int(idx[0] + 1) if len(idx) else len(lam)


def m_srs(lam, eps, M):
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    n = len(lam)
    k = np.arange(1, n + 1); m = k >= 3
    if m.sum() < 5:
        return r_true(lam, eps)
    le = np.log(np.maximum(lam[m], 1e-300))
    s1 = np.polyfit(k[m], le, 1); a = -s1[0]
    r2e = 1 - ((le - np.polyval(s1, k[m])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    s2 = np.polyfit(np.log(k[m]), le, 1)
    r2a = 1 - ((le - np.polyval(s2, np.log(k[m]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    if a * n < 3:
        return n
    if r2e >= r2a and a > 1e-12:
        return int(min(n, max(1, np.ceil((1 / (2 * a)) * np.log(1.0 / max(eps ** 2, 1e-300))))))
    return r_true(lam, eps)


def m_e99(lam):
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    c = np.cumsum(lam) / max(lam.sum(), 1e-300)
    return int(np.searchsorted(c, 0.99) + 1)


def m_gd(lam, M):
    sv = np.sqrt(np.sort(np.maximum(np.asarray(lam, float), 0))[::-1])
    sv = sv[sv > 0]
    if len(sv) < 4:
        return max(1, len(sv))
    med = np.median(sv[len(sv) // 2:])
    n = len(sv)
    beta = min(n, M) / max(n, M)
    lb = np.sqrt(2 * (beta + 1) + 8 * beta / ((beta + 1) + np.sqrt(beta ** 2 + 14 * beta + 1)))
    return int(max(1, min(int(np.sum(sv > lb * med * 2.858)), n)))


def m_aic(lam):
    p = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    p = p / max(p.sum(), 1e-300); n = len(p)
    best, bk = np.inf, 1
    for k in range(1, n + 1):
        v = n * np.log(max(p[k:].sum(), 1e-300)) + 2 * k
        if v < best:
            best, bk = v, k
    return bk


def m_bic(lam):
    p = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    p = p / max(p.sum(), 1e-300); n = len(p)
    best, bk = np.inf, 1
    for k in range(1, n + 1):
        v = n * np.log(max(p[k:].sum(), 1e-300)) + k * np.log(n)
        if v < best:
            best, bk = v, k
    return bk


def m_scree(lam):
    p = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    if len(p) < 5:
        return len(p)
    return int(np.argmax(np.diff(np.log(np.maximum(p, 1e-300)), 2)) + 3)


def m_cv(lam, M, grid=15):
    p = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    p = p / max(p.sum(), 1e-300); n = len(p)
    g = sorted(set(list(range(1, n + 1, max(1, n // grid))) + [n]))
    best, bk = np.inf, g[0]
    for k in g:
        v = p[k:].sum() + k / max(M, 1)
        if v < best:
            best, bk = v, k
    return int(bk)


METHODS = ["SRS", "E99_eps", "E99", "GD", "AIC", "BIC", "Scree", "CV"]


def run_method(name, lam, eps, M):
    return {"SRS": lambda: m_srs(lam, eps, M),
            "E99_eps": lambda: r_true(lam, eps),
            "E99": lambda: m_e99(lam),
            "GD": lambda: m_gd(lam, M),
            "AIC": lambda: m_aic(lam),
            "BIC": lambda: m_bic(lam),
            "Scree": lambda: m_scree(lam),
            "CV": lambda: m_cv(lam, M)}[name]()


def spectra_time(fn, n_traj=40):
    """时变：逐轨迹时间协方差 -> n = 时间点数"""
    p = os.path.join(PD, fn)
    if not os.path.exists(p):
        return None, None
    out = []
    with h5py.File(p, "r") as f:
        ten = f["tensor"]
        ntr = ten.shape[0]
        idx = np.linspace(0, ntr - 1, min(n_traj, ntr)).astype(int)
        M = int(ten.shape[1])
        for i in idx:
            field = np.asarray(ten[int(i)], dtype=np.float64)
            if field.ndim > 2:
                field = field.reshape(field.shape[0], -1)
            Y = np.nan_to_num(field - field.mean(0, keepdims=True))
            sv = np.linalg.svd(Y, compute_uv=False)
            lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
            if lam.sum() > 0:
                out.append(lam)
    return out, M


def spectra_space(fn, key="nu", n_samples=3000):
    """稳态：空间协方差（把 n_samples 个场展平为向量）-> n = 空间点数"""
    p = os.path.join(PD, fn)
    if not os.path.exists(p):
        return None, None
    with h5py.File(p, "r") as f:
        k = key if key in f else [x for x in f.keys()
                                  if isinstance(f[x], h5py.Dataset) and f[x].ndim >= 3][0]
        ds = f[k]
        n = ds.shape[0]
        idx = np.linspace(0, n - 1, min(n_samples, n)).astype(int)
        X = np.stack([np.asarray(ds[int(i)], dtype=np.float64).ravel() for i in idx])
    X = np.nan_to_num(X)
    X = X - X.mean(0, keepdims=True)
    sv = np.linalg.svd(X, compute_uv=False)
    lam = (sv ** 2) / max(X.shape[0] - 1, 1)
    return [lam], int(X.shape[0])


print("=" * 118)
print("路 B 步骤 1（修正）：PDEBench 完整秩选择基准（含 Darcy）")
print("=" * 118)
CASES = [("Advection beta=1.0", "1D_Advection_Sols_beta1.0.hdf5", "time"),
         ("Advection beta=4.0", "1D_Advection_Sols_beta4.0.hdf5", "time"),
         ("Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "time"),
         ("Darcy beta=1.0", "2D_DarcyFlow_beta1.0_Train.hdf5", "space")]

all_rows = []
for nm, fn, kind in CASES:
    if kind == "time":
        specs, M = spectra_time(fn, n_traj=40)
    else:
        specs, M = spectra_space(fn, n_samples=3000)
    if not specs:
        print(f"\n  [缺] {nm}")
        continue
    print(f"\n{'='*118}")
    print(f"### {nm}   ({'时间协方差' if kind=='time' else '空间协方差'})   "
          f"实例数 {len(specs)}   M = {M}   n = {len(specs[0])}")
    print(f"{'='*118}")
    print(f"  {'eps':>6}{'真值秩':>9}" + "".join(f"{m:>11}" for m in METHODS))
    for eps in EPS_LIST:
        rts = np.array([r_true(lam, eps) for lam in specs])
        vals = {m: np.array([run_method(m, lam, eps, M) for lam in specs])
                for m in METHODS}
        print(f"  {eps:>6.2f}{np.median(rts):>9.0f}" +
              "".join(f"{np.median(vals[m]):>11.0f}" for m in METHODS))
        print(f"  {'':>6}{'':>9}" +
              "".join(f"{(np.median(vals[m])/max(np.median(rts),1)):>10.2f}x"
                      for m in METHODS))
        for m in METHODS:
            all_rows.append(dict(system=nm, kind=kind, eps=eps, method=m, M=M,
                                 r_true=float(np.median(rts)),
                                 r_sel=float(np.median(vals[m])),
                                 ratio=float(np.median(vals[m]) / max(np.median(rts), 1)),
                                 satisfy_pct=float(np.mean(vals[m] >= rts) * 100),
                                 n=len(specs)))

json.dump(all_rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")

print()
print("=" * 118)
print("汇总①：秩/真值比的中位（1.0 = 完美）")
print("=" * 118)
print(f"  {'方法':>9}" + "".join(f"{c[0][:16]:>19}" for c in CASES))
for m in METHODS:
    line = f"  {m:>9}"
    for nm, _, _ in CASES:
        sub = [r for r in all_rows if r["system"] == nm and r["method"] == m]
        line += f"{np.median([s['ratio'] for s in sub]):>19.2f}" if sub else f"{'--':>19}"
    print(line)

print()
print("=" * 118)
print("汇总②：满足精度的比例（%）")
print("=" * 118)
print(f"  {'方法':>9}" + "".join(f"{c[0][:16]:>19}" for c in CASES))
for m in METHODS:
    line = f"  {m:>9}"
    for nm, _, _ in CASES:
        sub = [r for r in all_rows if r["system"] == nm and r["method"] == m]
        line += f"{np.median([s['satisfy_pct'] for s in sub]):>18.0f}%" if sub else f"{'--':>19}"
    print(line)
