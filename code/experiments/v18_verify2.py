# -*- coding: utf-8 -*-
"""V18 阶段二（修正版）：真实观测数据验证。

修正两处：
  1. measure_r 的累加逻辑写错 -> 改用正确的尾和公式（与预测同式但独立实现）
  2. lat 数组非单调 -> 用绝对值筛选纬度带
并扩展：多区域、多数据集、多分辨率。
"""
import os, io, json, time
import numpy as np
from scipy.io import netcdf_file
from scipy.linalg import svd as csvd

DATA = r"E:\nature投稿\探索1\数据"
OUT = r"E:\deepseekworkspace\experiments_v12"
PRED = json.load(io.open(os.path.join(OUT, "v18_predictions_real_data.json"), encoding="utf-8"))
TH = PRED["_meta"]["criteria"]
print("预测时间戳:", PRED["_meta"]["timestamp"], " 阈值:", json.dumps(TH, ensure_ascii=False))


def classify(lam, th=TH):
    lam = np.sort(np.asarray(lam, float))[::-1]
    lam = lam[lam > 1e-13 * lam[0]]
    if len(lam) < 8:
        return dict(cls="饱和", rule="R0", n=len(lam))
    n = len(lam); k = np.arange(1, n + 1)
    o = dict(n=n, rho=float(lam[-1] / lam[0]))
    lo = max(2, int(np.ceil(th["fit_lo"] * n))); hi = max(6, int(np.floor(th["fit_hi"] * n)))
    m = (k >= lo) & (k <= hi)
    y = np.log(lam[m])
    cE = np.polyfit(k[m], y, 1)
    r2E = 1 - ((y - np.polyval(cE, k[m]))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    cP = np.polyfit(np.log(k[m]), y, 1)
    r2P = 1 - ((y - np.polyval(cP, np.log(k[m])))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    a, b = float(-cE[0]), float(-cP[0])
    o.update(r2E=float(r2E), r2P=float(r2P), alpha=a, beta=b, alpha_n=float(a * n))
    if o["alpha_n"] < th["alpha_n_min"]:
        o.update(cls="饱和", rule="R1")
    elif max(r2E, r2P) < th["r2_min"]:
        o.update(cls="饱和", rule="R2")
    elif o["rho"] > th["rho_max"] and max(r2E, r2P) < th["r2_rho"]:
        o.update(cls="饱和", rule="R3")
    elif r2E >= r2P:
        o.update(cls="对数", rule="R4")
    else:
        o.update(cls="幂律", rule="R5")
    return o


def tail_rank(lam, eps):
    """独立实现：由尾和给出 r(ε)。"""
    lam = np.sort(np.asarray(lam, float))[::-1]
    e2 = lam ** 2
    cum = np.cumsum(e2)
    rel = np.sqrt(np.maximum(1.0 - cum / e2.sum(), 0.0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in eps], float)


def fitted_class(lam):
    """由 r(ε) 的双模型拟合独立判定实测类别。"""
    eps = np.logspace(-1, -8, 90)
    n = len(lam)
    r = tail_rank(lam, eps)
    m = (r > 0) & (r < n * 0.98)          # 排除饱和端
    if m.sum() < 6:
        return dict(cls="饱和", note=f"可拟合点 {int(m.sum())}")
    y, x = r[m], np.log(1 / eps[m]); sl, ic = np.polyfit(x, y, 1)
    r2l = 1 - ((y - (sl*x + ic))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    xp, yp = np.log(eps[m]), np.log(r[m]); p, c = np.polyfit(xp, yp, 1)
    r2p = 1 - ((yp - (p*xp + c))**2).sum() / max(((yp - yp.mean())**2).sum(), 1e-300)
    return dict(cls=("对数" if r2l > r2p else "幂律"), log_R2=float(r2l), pow_R2=float(r2p),
                r_min=int(r[m].min()), r_max=int(r[m].max()), n_pts=int(m.sum()))


f = netcdf_file(os.path.join(DATA, "OISSTv2_sst_mnmean.nc"), "r", mmap=False)
sstO = np.array(f.variables["sst"][:], dtype=np.float64)
latO = np.array(f.variables["lat"][:]); lonO = np.array(f.variables["lon"][:])
f.close()
sstO = np.where(sstO > 1e30, np.nan, sstO)
g = netcdf_file(os.path.join(DATA, "HadISST1_sst.nc"), "r", mmap=True)
sstH = np.array(g.variables["sst"][:], dtype=np.float64)
latH = np.array(g.variables["latitude"][:]); lonH = np.array(g.variables["longitude"][:])
g.close()
sstH = np.where(sstH > 1e30, np.nan, sstH)


def field(sst, lat, lon, lat_band, lon_band, t0=0, t1=None, stride=1):
    """lat_band: (abs_lat_min, abs_lat_max)；lon_band: (lo0, lo1) 或 None。"""
    S = sst[t0:t1]
    im = (np.abs(lat) >= lat_band[0]) & (np.abs(lat) <= lat_band[1])
    if lon_band:
        jo = (lon >= lon_band[0]) & (lon <= lon_band[1])
        S = S[:, im, :][:, :, jo]
    else:
        S = S[:, im, :]
    S = S[:, ::stride, ::stride]
    T, P, Q = S.shape
    X = S.reshape(T, P*Q)
    X = X - X.mean(0, keepdims=True)
    good = ~np.isnan(X).any(0)
    return X[:, good], int(im.sum()), int(S.shape[2])


REGIONS = {
 "TP":  (0, 25, (120, 290)),      # 热带太平洋
 "TNA": (0, 25, (280, 360)),      # 热带北大西洋
 "NP":  (25, 55, (140, 250)),     # 北太平洋
 "GLB": (0, 60, None),            # 全球中低纬
}
CASES = {}
for rn, (a0, a1, lb) in REGIONS.items():
    st = 4 if rn == "GLB" else 1
    try:
        X, nl, nlon = field(sstO, latO, lonO, (a0, a1), lb, t1=494, stride=st)
        if X.shape[1] > 30:
            CASES[f"OISST_{rn}"] = X
    except Exception as e:
        print(f"  OISST_{rn} 失败: {e}")
    try:
        X, nl, nlon = field(sstH, latH, lonH, (a0, a1), lb, t0=1560, t1=1879, stride=st)
        if X.shape[1] > 30:
            CASES[f"HadISST_{rn}"] = X
    except Exception as e:
        print(f"  HadISST_{rn} 失败: {e}")
# 长记录
CASES["HadISST_TP_1870_2026"] = field(sstH, latH, lonH, (0, 25), (120, 290), t0=0, t1=1879, stride=2)[0]

EPS = np.array([1e-1, 3e-2, 1e-2, 3e-3, 1e-3])
print("\n" + "=" * 112)
print("真实观测数据：事前预测 vs 独立验证")
print("=" * 112)
print(f"  {'案例':<26}{'样本':>6}{'空间点':>8}{'αn':>8}{'预测':>7}{'实测':>7}{'一致':>6}"
      f"  {'r(1e-1)':>8}{'r(1e-3)':>8}")
print("-" * 112)
RES = {}; hit = tot = 0
for nm, X in CASES.items():
    sv = csvd(X - X.mean(0, keepdims=True), compute_uv=False)
    lam = sv ** 2
    c = classify(lam); fc = fitted_class(lam)
    r = tail_rank(lam, EPS)
    ok = c["cls"] == fc["cls"]; hit += ok; tot += 1
    RES[nm] = dict(samples=int(X.shape[0]), dims=int(X.shape[1]), predict=c, fitted=fc,
                   r_at_eps=r.tolist(), agree=bool(ok))
    print(f"  {nm:<26}{X.shape[0]:>6}{X.shape[1]:>8}{c.get('alpha_n',float('nan')):>8.2f}"
          f"{c['cls']:>7}{fc['cls']:>7}{'✓' if ok else '✗':>6}"
          f"{int(r[0]):>8}{int(r[-1]):>8}")
print("-" * 112)
print(f"  类别一致率: {hit}/{tot} = {hit/tot*100:.1f}%")

print("\n  事前预测（OISSTv2_TP / HadISST1_TP）与独立测量的秩逐项比对")
print(f"  {'案例':<22}{'来源':<8}" + "".join(f"{'ε='+format(e,'g'):>10}" for e in EPS))
for key in ("OISSTv2_TP", "HadISST1_TP"):
    if key in PRED:
        print(f"  {key:<22}{'预测':<8}" + "".join(f"{int(v):>10}" for v in PRED[key]["predicted_rank"]))
    got = RES.get(key) or RES.get(key.replace("OISSTv2_", "OISST_").replace("HadISST1_", "HadISST_"))
    if got:
        print(f"  {'':<22}{'实测':<8}" + "".join(f"{int(v):>10}" for v in got["r_at_eps"]))

json.dump(dict(thresholds=TH, cases=RES, class_hit=hit, class_tot=tot,
               verify_time=time.strftime("%Y-%m-%d %H:%M:%S")),
          io.open(os.path.join(OUT, "v18_verification_real_data.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nsaved v18_verification_real_data.json")
