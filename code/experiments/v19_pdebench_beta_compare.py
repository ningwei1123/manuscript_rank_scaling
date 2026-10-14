# -*- coding: utf-8 -*-
"""PDEBench Advection β=1.0 vs β=4.0：判类是否随谱指数变化？

这是 v15 承诺但未完成的检验：两个 β 值的对照。
"""
import io, json, os
import numpy as np
import h5py

D = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
OUT = r"E:\deepseekworkspace\experiments_v12\v19_pdebench_beta_compare.json"


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
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    r2p = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / ((lg - lg.mean()) ** 2).sum()
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / ((r[m] - r[m].mean()) ** 2).sum()
    sc = "EXP" if r2e > r2a else "ALG"
    rc = "ALG" if r2p > r2l else "EXP"
    return sc, rc, (sc == rc), float(-sa[0]), float(pp[0]), dict(
        r2e=float(r2e), r2a=float(r2a), r2l=float(r2l), r2p=float(r2p),
        r1e3=float(ranks(lam, [1e-3])[0]), r1e6=float(ranks(lam, [1e-6])[0]))


print("=" * 112)
print("PDEBench Advection：β=1.0 vs β=4.0")
print("=" * 112)
res = {}
for beta_name, fn in (("beta1.0", "1D_Advection_Sols_beta1.0.hdf5"),
                      ("beta4.0", "1D_Advection_Sols_beta4.0.hdf5")):
    p = os.path.join(D, fn)
    if not os.path.exists(p):
        print(f"[缺] {fn}"); continue
    with h5py.File(p, "r") as f:
        ba = float(f.attrs.get("beta", float("nan")))
        ten = f["tensor"]
        ntr, nt, nx = ten.shape
        print(f"\n### {fn}  beta_attr={ba}  shape={ten.shape} ###")
        N = 24
        agg = {"EXP": 0, "ALG": 0, "agree": 0, "beta_fit": [], "rank_exp": [],
               "r1e3": [], "r1e6": [], "r2e": [], "r2a": [], "r2l": [], "r2p": []}
        for i in range(N):
            field = np.asarray(ten[i], dtype=np.float64)
            Y = field - field.mean(0, keepdims=True)
            sv = np.linalg.svd(Y, compute_uv=False)
            lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
            sc, rc, ag, bf, re_, d = classify(lam)
            agg["EXP" if sc == "EXP" else "ALG"] += 1
            agg["agree"] += int(ag)
            agg["beta_fit"].append(bf); agg["rank_exp"].append(re_)
            agg["r1e3"].append(d["r1e3"]); agg["r1e6"].append(d["r1e6"])
            for kk in ("r2e", "r2a", "r2l", "r2p"):
                agg[kk].append(d[kk])
        s = {k: (float(np.median(v)) if isinstance(v, list) and v else v)
             for k, v in agg.items()}
        res[beta_name] = dict(beta_attr=ba, n_traj=N, agree_rate=agg["agree"] / N, **s)
        print(f"  一致率 {agg['agree']}/{N} = {agg['agree']/N*100:.0f}%")
        print(f"  谱类: EXP×{agg['EXP']}  ALG×{agg['ALG']}")
        print(f"  beta_fit 中位 {np.median(agg['beta_fit']):.4f}  "
              f"范围 {min(agg['beta_fit']):.3f}..{max(agg['beta_fit']):.3f}")
        print(f"  rank(1e-3) 中位 {np.median(agg['r1e3']):.0f}   "
              f"rank(1e-6) 中位 {np.median(agg['r1e6']):.0f}")
        print(f"  R²: exp={np.median(agg['r2e']):.4f} alg={np.median(agg['r2a']):.4f} "
              f"log={np.median(agg['r2l']):.4f} pow={np.median(agg['r2p']):.4f}")

if len(res) == 2:
    print()
    print("=" * 112)
    print("对照：判类是否随 β 变化？")
    print("=" * 112)
    print(f"  {'β':>8}{'β_attr':>9}{'一致率':>10}{'β_fit 中位':>13}"
          f"{'rank(1e-3)':>13}{'rank(1e-6)':>13}")
    for k, v in res.items():
        print(f"  {k:>8}{v['beta_attr']:>9.1f}{v['agree_rate']*100:>9.0f}%"
              f"{v['beta_fit']:>13.4f}{v['r1e3']:>13.0f}{v['r1e6']:>13.0f}")
    b1, b4 = res["beta1.0"], res["beta4.0"]
    print()
    print(f"  β_fit 变化: {b1['beta_fit']:.3f} -> {b4['beta_fit']:.3f}  "
          f"({'β 增大使谱更陡' if b4['beta_fit'] > b1['beta_fit'] else '反向'})")
    print(f"  一致率变化: {b1['agree_rate']*100:.0f}% -> {b4['agree_rate']*100:.0f}%")

json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
