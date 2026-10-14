# -*- coding: utf-8 -*-
"""路 1 正式检验：稿件定义下的「诊断可迁移性」三方判类。

稿件逻辑 = 三方比较：
    谱形（拟合误差/指数）  ->  预测的类
    秩-精度曲线形状        ->  实测的类
    两者是否一致           ->  "迁移"与否

关键：谱是**指数式**衰减还是**代数式**衰减？
  指数：log λ_k 对 k 线性
  代数：log λ_k 对 log k 线性
以 R² 较大者为准（并记录两者之差）。
"""
import io, os, json, datetime
import numpy as np
from scipy.io import netcdf_file

OUT = r"E:\deepseekworkspace\experiments_v12"
D = r"E:\nature投稿\探索1\数据"
FILL = -1e29                      # HadISST1 陆地/冰的填充值

REGIONS = {
    "Nino3.4":           {"lat": (-5, 5),   "lon": (190, 240)},
    "Nino3":             {"lat": (-5, 5),   "lon": (210, 270)},
    "TropicalAtlanticW": {"lat": (-20, 20), "lon": (280, 360)},
    "TropicalAtlanticE": {"lat": (-20, 20), "lon": (0, 20)},
    "NorthPacific":      {"lat": (30, 50),  "lon": (150, 240)},
    "NorthAtlantic":     {"lat": (40, 60),  "lon": (300, 340)},
    "IndianOcean":       {"lat": (-20, 20), "lon": (40, 110)},
    "SouthernOcean":     {"lat": (-60, -40), "lon": (0, 360)},
}


def parse_times(t, base_year):
    base = datetime.date(base_year, 1, 1)
    return [(base + datetime.timedelta(days=float(v))).year,
            (base + datetime.timedelta(days=float(v))).month] and \
           [(base + datetime.timedelta(days=float(v))) for v in t]


def get_time(t, base_year):
    base = datetime.date(base_year, 1, 1)
    ds = [base + datetime.timedelta(days=float(v)) for v in t]
    return [d.year for d in ds], [d.month for d in ds]


def load(path, kind):
    f = netcdf_file(path, "r", mmap=False)
    kl = "latitude" if kind == "hadisst" else "lat"
    ko = "longitude" if kind == "hadisst" else "lon"
    lat = np.asarray(f.variables[kl][:], float)
    lon = np.asarray(f.variables[ko][:], float)
    sst = np.asarray(f.variables["sst"][:], float)
    t = np.asarray(f.variables["time"][:], float)
    f.close()
    sst = np.where(sst <= FILL, np.nan, sst)     # 正确剔除填充值
    yy, mm = get_time(t, 1870 if kind == "hadisst" else 1800)
    return lat, lon, sst, yy, mm


def lon_mask(lon, lo, hi):
    L = lon % 360.0
    lo, hi = lo % 360.0, hi % 360.0
    return (L >= lo) & (L <= hi) if lo <= hi else (L >= lo) | (L <= hi)


def build(path, kind, latr, lonr, min_frac=0.95):
    lat, lon, sst, yy, mm = load(path, kind)
    la = np.where((lat >= latr[0]) & (lat <= latr[1]))[0]
    lo = np.where(lon_mask(lon, lonr[0], lonr[1]))[0]
    sub = sst[:, la][:, :, lo]
    T, A, B = sub.shape
    X = sub.reshape(T, A * B)
    frac = np.isfinite(X).mean(0)
    keep = frac >= min_frac
    if keep.sum() < 10:
        return None
    Xk = X[:, keep]
    mu = np.nanmean(Xk, 0, keepdims=True)
    Xk = np.where(np.isfinite(Xk), Xk, mu)
    mon = np.array(mm)
    for m in range(1, 13):
        s = mon == m
        if s.sum() >= 3:
            Xk[s] = Xk[s] - Xk[s].mean(0, keepdims=True)
    tt = np.arange(T, dtype=float)
    Xk = Xk - np.column_stack([np.polyval(np.polyfit(tt, Xk[:, j], 1), tt)
                               for j in range(Xk.shape[1])])
    w = np.repeat(np.cos(np.deg2rad(lat[la])), B)[keep]
    w = w / w.sum()
    return Xk, w, dict(nlat=len(la), nlon=len(lo), n_kept=int(keep.sum()),
                       n_tot=int(keep.size), T=T, years=[yy[0], yy[-1]])


def cov_spec(X, w):
    Y = X - X.mean(0, keepdims=True)
    Y = Y * np.sqrt(w)[None, :]
    sv = np.linalg.svd(Y, compute_uv=False)
    return (sv ** 2) / (Y.shape[0] - 1)


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def classify(lam):
    """三方判类：谱形 vs 秩律形。"""
    lam = np.sort(lam)[::-1]; n = len(lam); k = np.arange(1, n + 1)
    pos = lam > 0
    # 谱：指数 vs 代数
    s_exp = np.polyfit(k[pos], np.log(lam[pos]), 1)
    r2_exp = 1 - ((np.log(lam[pos]) - np.polyval(s_exp, k[pos])) ** 2).sum() / \
                  ((np.log(lam[pos]) - np.log(lam[pos]).mean()) ** 2).sum()
    s_alg = np.polyfit(np.log(k[pos]), np.log(lam[pos]), 1)
    r2_alg = 1 - ((np.log(lam[pos]) - np.polyval(s_alg, np.log(k[pos]))) ** 2).sum() / \
                  ((np.log(lam[pos]) - np.log(lam[pos]).mean()) ** 2).sum()
    spec_class = "ALG" if r2_alg > r2_exp else "EXP"
    # 秩律
    eps = np.logspace(np.log10(0.3), np.log10(1e-4), 60)
    r = ranks(lam, eps)
    m = r < n * 0.999
    if m.sum() < 8:
        m = np.ones_like(r, bool)
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / ((r[m] - r[m].mean()) ** 2).sum()
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    r2p = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / ((lg - lg.mean()) ** 2).sum()
    rank_class = "ALG" if r2p > r2l else "EXP"
    return dict(spec_class=spec_class, rank_class=rank_class,
                agree=(spec_class == rank_class),
                r2_spec_exp=float(r2_exp), r2_spec_alg=float(r2_alg),
                spec_alpha=float(-s_exp[0]), spec_beta=float(-s_alg[0] / 2),
                r2_rank_log=float(r2l), r2_rank_pow=float(r2p),
                rank_pow_alpha=float(pp[0]), r_at_1e_3=float(ranks(lam, [1e-3])[0]), n=n)


print("=" * 112)
print("路 1 正式检验：稿件定义下的诊断可迁移性（标准区域 + 去季节 + 去趋势 + 面积加权）")
print("=" * 112)
summary = {}
for name, path, kind in (("HadISST1", os.path.join(D, "HadISST1_sst.nc"), "hadisst"),
                         ("OISSTv2", os.path.join(D, "OISSTv2_sst_mnmean.nc"), "oisst")):
    print(f"\n--- {name} ---")
    print(f"  {'region':<20}{'格点':>10}{'谱类':>7}{'秩类':>7}{'一致':>6}"
          f"{'R²spec_exp':>11}{'R²spec_alg':>11}{'R²rank_log':>11}{'R²rank_pow':>11}")
    for rn, r in REGIONS.items():
        out = build(path, kind, r["lat"], r["lon"])
        if out is None:
            print(f"  {rn:<20} 有效格点不足"); continue
        X, w, meta = out
        c = classify(cov_spec(X, w))
        summary[f"{name}_{rn}"] = dict(c, region=r, **meta)
        flag = "✓" if c["agree"] else "✗"
        print(f"  {rn:<20}{meta['n_kept']:>5}/{meta['n_tot']:<5}"
              f"{c['spec_class']:>7}{c['rank_class']:>7}{flag:>5}"
              f"{c['r2_spec_exp']:>11.4f}{c['r2_spec_alg']:>11.4f}"
              f"{c['r2_rank_log']:>11.4f}{c['r2_rank_pow']:>11.4f}")

json.dump(summary, io.open(os.path.join(OUT, "v12_transfer_standard.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
n = len(summary)
ag = sum(1 for v in summary.values() if v["agree"])
print(f"\n一致: {ag}/{n} = {100*ag/max(n,1):.0f}%")
print(f"谱类分布: EXP={sum(1 for v in summary.values() if v['spec_class']=='EXP')}, "
      f"ALG={sum(1 for v in summary.values() if v['spec_class']=='ALG')}")
print(f"秩类分布: EXP={sum(1 for v in summary.values() if v['rank_class']=='EXP')}, "
      f"ALG={sum(1 for v in summary.values() if v['rank_class']=='ALG')}")
print("已保存 v12_transfer_standard.json")
