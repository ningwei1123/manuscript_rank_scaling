# -*- coding: utf-8 -*-
"""PDEBench 1D Burgers（Nu=0.01）分析：非线性 PDE 上的判类检验。

与 Advection 的关键差别：Burgers 有 u·u_x 非线性项 -> 模态混合 -> 协方差非退化。
"""
import io, json, os
import numpy as np
import h5py

D = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
OUT = r"E:\deepseekworkspace\experiments_v12\v19_pdebench_burgers.json"


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
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
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    denom = ((lg - lg.mean()) ** 2).sum()
    r2p = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / denom if denom > 1e-30 else 0.0
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    den2 = ((r[m] - r[m].mean()) ** 2).sum()
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / den2 if den2 > 1e-30 else 0.0
    sc = "EXP" if r2e > r2a else "ALG"
    rc = "ALG" if r2p > r2l else "EXP"
    return sc, rc, (sc == rc), float(-sa[0]), float(pp[0]), dict(
        r2e=float(r2e), r2a=float(r2a), r2l=float(r2l), r2p=float(r2p),
        r1e3=float(ranks(lam, [1e-3])[0]), r1e6=float(ranks(lam, [1e-6])[0]))


p = os.path.join(D, "1D_Burgers_Sols_Nu0.01.hdf5")
print("=" * 112)
print("PDEBench 1D Burgers (Nu=0.01) —— 非线性 PDE 检验")
print("=" * 112)
with h5py.File(p, "r") as f:
    print(f"  根属性: {dict(list(f.attrs.items())[:6])}")
    for k in f.keys():
        o = f[k]
        if isinstance(o, h5py.Dataset):
            print(f"    {k:<22} shape={str(o.shape):<24} dtype={o.dtype}")
    fields = [k for k in f.keys()
              if isinstance(f[k], h5py.Dataset) and f[k].ndim >= 2 and k != "t-coordinate"]
    print(f"  场数据集: {fields}")

    key = fields[0] if fields else list(f.keys())[0]
    ten = f[key]
    print(f"\n  === 场 {key}  shape={ten.shape} ===")
    ntr, nt, nx = ten.shape

    N = 24
    agg = dict(EXP=0, ALG=0, agree=0, beta=[], rexp=[], r1e3=[], r1e6=[],
               r2e=[], r2a=[], r2l=[], r2p=[])
    print(f"\n  {'轨迹':>5}{'谱类':>6}{'秩类':>6}{'一致':>6}{'beta_fit':>11}"
          f"{'秩指数':>10}{'r(1e-3)':>9}{'r(1e-6)':>9}{'R2log':>8}{'R2pow':>8}")
    for i in range(N):
        field = np.asarray(ten[i], dtype=np.float64)
        if field.ndim > 2:
            field = field.reshape(field.shape[0], -1)
        field = np.nan_to_num(field)
        Y = field - field.mean(0, keepdims=True)
        sv = np.linalg.svd(Y, compute_uv=False)
        lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
        sc, rc, ag, bf, re_, d = classify(lam)
        agg["EXP" if sc == "EXP" else "ALG"] += 1
        agg["agree"] += int(ag)
        agg["beta"].append(bf); agg["rexp"].append(re_)
        agg["r1e3"].append(d["r1e3"]); agg["r1e6"].append(d["r1e6"])
        for kk in ("r2e", "r2a", "r2l", "r2p"):
            agg[kk].append(d[kk])
        if i < 12:
            print(f"  {i:>5}{sc:>6}{rc:>6}{'Y' if ag else 'N':>6}{bf:>11.4f}"
                  f"{re_:>10.4f}{d['r1e3']:>9.0f}{d['r1e6']:>9.0f}"
                  f"{d['r2l']:>8.4f}{d['r2p']:>8.4f}")

    print()
    print(f"  一致率 {agg['agree']}/{N} = {agg['agree']/N*100:.0f}%")
    print(f"  谱类: EXP×{agg['EXP']}  ALG×{agg['ALG']}")
    print(f"  beta_fit 中位 {np.median(agg['beta']):.4f}  "
          f"范围 {min(agg['beta']):.3f}..{max(agg['beta']):.3f}")
    print(f"  秩指数 中位 {np.median(agg['rexp']):.4f}")
    print(f"  rank(1e-3) 中位 {np.median(agg['r1e3']):.0f}    "
          f"rank(1e-6) 中位 {np.median(agg['r1e6']):.0f}")
    print(f"  R² 中位: exp={np.median(agg['r2e']):.4f} alg={np.median(agg['r2a']):.4f} "
          f"log={np.median(agg['r2l']):.4f} pow={np.median(agg['r2p']):.4f}")

    res = dict(file=os.path.basename(p), shape=list(ten.shape),
               agree_rate=agg["agree"] / N,
               spec=dict(EXP=agg["EXP"], ALG=agg["ALG"]),
               beta_median=float(np.median(agg["beta"])),
               rank_exp_median=float(np.median(agg["rexp"])),
               r1e3_median=float(np.median(agg["r1e3"])),
               r1e6_median=float(np.median(agg["r1e6"])),
               r2=dict(exp=float(np.median(agg["r2e"])), alg=float(np.median(agg["r2a"])),
                       log=float(np.median(agg["r2l"])), pow=float(np.median(agg["r2p"]))))

json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
