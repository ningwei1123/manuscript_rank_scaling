# -*- coding: utf-8 -*-
"""V20 严格检验 D（修正版）：约定**事前固定**下的干净判定。

关键教训（来自 D1/D2）：
  谱形判定与 r(ε) 判定都**依赖拟合窗与范数约定**。
  若两边各自选约定，比较就失去意义。
  故此处固定一套约定（与稿件一致）：
     范数 = 相对 Frobenius；拟合窗 = 谱中部[0.10,0.90]；
     r(ε) 拟合窗 = 未饱和区（r < 0.98n），ε∈[1e-1, 1e-3.5]
并**报告约定敏感性**（换约定时结论如何变）。
"""
import io, os, json
import numpy as np
from scipy.io import netcdf_file
from scipy.linalg import svd as csvd

DATA = r"E:\nature投稿\探索1\数据"
OUT = r"E:\deepseekworkspace\experiments_v12"
EPS = np.logspace(-1, -3.5, 16)

f = netcdf_file(os.path.join(DATA, "OISSTv2_sst_mnmean.nc"), "r", mmap=False)
sstO = np.array(f.variables["sst"][:], dtype=np.float64)
latO = np.array(f.variables["lat"][:]); lonO = np.array(f.variables["lon"][:]); f.close()
sstO = np.where(sstO > 1e30, np.nan, sstO)
g = netcdf_file(os.path.join(DATA, "HadISST1_sst.nc"), "r", mmap=True)
sstH = np.array(g.variables["sst"][:], dtype=np.float64)
latH = np.array(g.variables["latitude"][:]); lonH = np.array(g.variables["longitude"][:]); g.close()
sstH = np.where(sstH > 1e30, np.nan, sstH)


def field(sst, lat, lon, ab, lb, t0=0, t1=None, stride=1):
    S = sst[t0:t1]
    im = (np.abs(lat) >= ab[0]) & (np.abs(lat) <= ab[1])
    if lb:
        jo = (lon >= lb[0]) & (lon <= lb[1]); S = S[:, im, :][:, :, jo]
    else:
        S = S[:, im, :]
    S = S[:, ::stride, ::stride]
    T, P, Q = S.shape
    X = S.reshape(T, P * Q); X = X - X.mean(0, keepdims=True)
    return X[:, ~np.isnan(X).any(0)]


REG = {"TP": (0, 25, (120, 290)), "TNA": (0, 25, (280, 360)),
       "NP": (25, 55, (140, 250)), "GLB": (0, 60, None)}
CASES = {}
for rn, (a0, a1, lb) in REG.items():
    st = 4 if rn == "GLB" else 1
    X = field(sstO, latO, lonO, (a0, a1), lb, t1=494, stride=st)
    if min(X.shape) > 12:
        CASES[f"OISST_{rn}"] = X
    X = field(sstH, latH, lonH, (a0, a1), lb, t0=1560, t1=1879, stride=st)
    if min(X.shape) > 12:
        CASES[f"HadISST_{rn}"] = X
CASES["HadISST_TP_long"] = field(sstH, latH, lonH, (0, 25), (120, 290), t0=0, t1=1879, stride=2)


def fit_shape(lam, lo_f=0.10, hi_f=0.90):
    n = len(lam); k = np.arange(1, n + 1)
    lo, hi = max(2, int(lo_f * n)), max(6, int(hi_f * n))
    m = (k >= lo) & (k <= hi)
    if m.sum() < 6:
        return None
    y = np.log(lam[m])
    cE = np.polyfit(k[m], y, 1)
    r2E = 1 - ((y - np.polyval(cE, k[m]))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    cP = np.polyfit(np.log(k[m]), y, 1)
    r2P = 1 - ((y - np.polyval(cP, np.log(k[m])))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    return dict(alpha=float(-cE[0]), beta=float(-cP[0]), r2E=float(r2E), r2P=float(r2P),
                shape=("指数" if r2E >= r2P else "幂律"))


def rank_relF(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def rank_op(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    tail = np.cumsum((lam ** 2)[::-1])[::-1]
    rel = np.sqrt(np.maximum(tail / lam[0] ** 2, 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def rank_en(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    rel = np.sqrt(np.maximum(1 - np.cumsum(lam) / lam.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def cls_of_curve(lam, rf):
    n = len(lam)
    r = rf(lam, EPS)
    m = (r > 0) & (r < n * 0.98)
    if m.sum() < 6:
        return "饱和", np.nan, np.nan
    y, x = r[m], np.log(1 / EPS[m]); sl, ic = np.polyfit(x, y, 1)
    r2l = 1 - ((y - (sl*x + ic))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    xp, yp = np.log(EPS[m]), np.log(r[m]); p, c = np.polyfit(xp, yp, 1)
    r2p = 1 - ((yp - (p*xp + c))**2).sum() / max(((yp - yp.mean())**2).sum(), 1e-300)
    return ("对数" if r2l > r2p else "幂律"), float(r2l), float(r2p)


print("=" * 110)
print("D（修正）：约定**事前固定**（相对 Frobenius + 窗口[0.10,0.90]）")
print("=" * 110)
print(f"  {'案例':<18}{'n':>6}{'谱形':>6}{'R²_E':>7}{'R²_P':>7}"
      f"{'实测类别':>10}{'log R²':>8}{'pow R²':>8}  一致")
print("-" * 110)
D = {}; hit = tot = 0
for nm, X in CASES.items():
    lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
    sh = fit_shape(lam)
    if sh is None:
        continue
    mc, r2l, r2p = cls_of_curve(lam, rank_relF)
    pred = sh["shape"]
    ok = (pred == mc); hit += ok; tot += 1
    D[nm] = dict(n=len(lam), shape=sh, measured=mc, log_R2=r2l, pow_R2=r2p, agree=bool(ok))
    print(f"  {nm:<18}{len(lam):>6}{pred:>6}{sh['r2E']:>7.3f}{sh['r2P']:>7.3f}"
          f"{mc:>10}{r2l:>8.3f}{r2p:>8.3f}  {'✓' if ok else '✗'}")
print("-" * 110)
print(f"  一致率（约定固定）: {hit}/{tot} = {hit/tot*100:.1f}%")

print("\n  约定敏感性：换范数时实测类别如何变")
print(f"  {'案例':<18}{'相对Fro':>10}{'operator':>10}{'能量':>8}  稳定?")
for nm, X in CASES.items():
    lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
    cs = {}
    for t, rf in (("relF", rank_relF), ("op", rank_op), ("en", rank_en)):
        cs[t] = cls_of_curve(lam, rf)[0]
    D[nm]["norms"] = cs
    print(f"  {nm:<18}{cs['relF']:>10}{cs['op']:>10}{cs['en']:>8}"
          f"  {'✓' if len(set(cs.values())) == 1 else '✗ 随约定变'}")

print("\n" + "=" * 110)
print("D3 阈值重标定（固定约定下）")
print("=" * 110)
print(f"  {'αn_min':>8}{'一致数':>8}{'一致率':>9}")
best = None
for th in np.arange(1.0, 41.0, 2.0):
    h = t = 0
    for nm, X in CASES.items():
        lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
        sh = fit_shape(lam)
        if sh is None:
            continue
        an = sh["alpha"] * len(lam)
        pred = "饱和" if (an < th or max(sh["r2E"], sh["r2P"]) < 0.90) else sh["shape"]
        mc = cls_of_curve(lam, rank_relF)[0]
        t += 1; h += (pred == mc)
    print(f"  {th:>8.1f}{h:>8}{h/max(t,1)*100:>8.1f}%")
    if best is None or h/max(t, 1) > best[1]:
        best = (th, h/max(t, 1))
print(f"\n  最优 αn_min = {best[0]:.1f}，一致率 {best[1]*100:.1f}%")
json.dump(dict(cases=D, hit=hit, tot=tot, best_th=best[0], best_rate=best[1]),
          io.open(os.path.join(OUT, "v20_check_D.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nsaved v20_check_D.json")
