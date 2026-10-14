# -*- coding: utf-8 -*-
"""路 1 加强对照：少数主导模态 + 空间相关的合成场。

目的：排除「观测数据的低一致率来自模态数少或空间相关性」这一解释。
做法：构造地位数（rank）远小于维数的合成场，谱仍为指数式，
      并叠加空间相关结构，再测一致率。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v12_baseline2.json"


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def classify(lam):
    lam = np.sort(lam)[::-1]; n = len(lam); k = np.arange(1, n + 1); pos = lam > 0
    le = np.log(lam[pos])
    se = np.polyfit(k[pos], le, 1)
    r2e = 1 - ((le - np.polyval(se, k[pos])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    sa = np.polyfit(np.log(k[pos]), le, 1)
    r2a = 1 - ((le - np.polyval(sa, np.log(k[pos]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
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
    sc = "EXP" if r2e > r2a else "ALG"
    rc = "ALG" if r2p > r2l else "EXP"
    return sc, rc, sc == rc, r2e, r2a, r2l, r2p


def gen(T, P, alpha, n_modes, noise, seed, corr_len=5):
    """少数主导模态 + 空间相关 + 时间白噪声（矩阵正态）。"""
    r = np.random.default_rng(seed)
    # 空间相关矩阵（指数衰减）
    d = np.abs(np.arange(P)[:, None] - np.arange(P)[None, :])
    C = np.exp(-d / corr_len)
    L = np.linalg.cholesky(C + 1e-8 * np.eye(P))
    lam = np.exp(-alpha * np.arange(n_modes))
    lam = np.concatenate([lam, np.full(P - n_modes, noise)])
    Z = r.standard_normal((T, P))
    X = (Z * np.sqrt(lam)[None, :]) @ L.T
    return X


print("=" * 106)
print("加强对照：少数主导模态 + 空间相关")
print("=" * 106)
res = {}
CASES = [
    (1879, 500, 0.05, 20,  1e-6, "T=1879 P=500 m=20  相关5"),
    (1879, 500, 0.05, 50,  1e-6, "T=1879 P=500 m=50  相关5"),
    (1879, 500, 0.02, 50,  1e-6, "T=1879 P=500 m=50  相关5 α=0.02"),
    (494,  500, 0.05, 20,  1e-6, "T=494  P=500 m=20  相关5"),
    (494,  500, 0.05, 50,  1e-6, "T=494  P=500 m=50  相关5"),
    (494,  500, 0.05, 20,  1e-3, "T=494  P=500 m=20  相关5 噪声1e-3"),
    (1879, 500, 0.05, 20,  1e-3, "T=1879 P=500 m=20  相关5 噪声1e-3"),
    (1879, 500, 0.05, 20,  1e-2, "T=1879 P=500 m=20  相关5 噪声1e-2"),
]
for T, P, alpha, m, nf, lab in CASES:
    ag, scs, rcs, gaps = [], [], [], []
    for s in range(12):
        X = gen(T, P, alpha, m, nf, 2000 + s)
        Y = X - X.mean(0, keepdims=True)
        sv = np.linalg.svd(Y, compute_uv=False)
        lam = (sv ** 2) / (Y.shape[0] - 1)
        sc, rc, a, r2e, r2a, r2l, r2p = classify(lam)
        ag.append(a); scs.append(sc); rcs.append(rc); gaps.append(abs(r2e - r2a))
    rate = float(np.mean(ag))
    res[lab] = dict(agree_rate=rate, spec={"EXP": scs.count("EXP"), "ALG": scs.count("ALG")},
                    rank={"EXP": rcs.count("EXP"), "ALG": rcs.count("ALG")},
                    median_gap=float(np.median(gaps)))
    print(f"  {lab:<34} 一致率={rate*100:>5.0f}%  谱 EXP×{scs.count('EXP'):>2}/ALG×{scs.count('ALG'):<2}"
          f"  秩 EXP×{rcs.count('EXP'):>2}/ALG×{rcs.count('ALG'):<2}  |gap|中位={np.median(gaps):.4f}")

base = [v["agree_rate"] for v in res.values()]
print(f"\n  合成加强对照一致率范围: {min(base)*100:.0f}% – {max(base)*100:.0f}%")
print(f"  观测数据: 29% (4/14)")
print("\n  解读：若加强对照仍接近 100%，则观测数据的失败不能由模态数少/空间相关/噪声地板解释。")
json.dump(res, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已保存 v12_baseline2.json")
