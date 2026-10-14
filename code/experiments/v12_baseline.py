# -*- coding: utf-8 -*-
"""路 1 关键对照：一致性检验的**有限样本基线**。

问题：观测数据「谱判 EXP、秩判 ALG」的不一致率是 10/14。
      但合成数据（干净指数谱 + 噪声地板）是否也会出现同样的不一致？
      若是，则不能把不一致归因于观测数据的特殊性。

方法：生成与观测数据**同规模**的合成场（T 与 n_dim 匹配），
      谱为指数衰减 + 可控噪声地板，比较三方判类的一致率。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v12_finite_sample_baseline.json"
rng = np.random.default_rng(7)


def ranks(lam, eps):
    lam = np.sort(lam)[::-1]; e2 = lam ** 2
    rel = np.sqrt(np.maximum(1 - np.cumsum(e2) / e2.sum(), 0))
    return np.array([int(np.searchsorted(-rel, -e)) + 1 for e in np.atleast_1d(eps)], float)


def spectrum_fits(lam):
    lam = np.sort(lam)[::-1]; n = len(lam); k = np.arange(1, n + 1)
    pos = lam > 0
    le = np.log(lam[pos])
    se = np.polyfit(k[pos], le, 1)
    r2e = 1 - ((le - np.polyval(se, k[pos])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    sa = np.polyfit(np.log(k[pos]), le, 1)
    r2a = 1 - ((le - np.polyval(sa, np.log(k[pos]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    return ("EXP" if r2e > r2a else "ALG"), float(r2e), float(r2a)


def rank_fits(lam, eps_lo=0.3, eps_hi=1e-4):
    eps = np.logspace(np.log10(eps_lo), np.log10(eps_hi), 60)
    r = ranks(lam, eps); n = len(lam)
    m = r < n * 0.999
    if m.sum() < 8:
        m = np.ones_like(r, bool)
    sl = np.polyfit(np.log(1 / eps[m]), r[m], 1)
    r2l = 1 - ((r[m] - np.polyval(sl, np.log(1 / eps[m]))) ** 2).sum() / ((r[m] - r[m].mean()) ** 2).sum()
    lg = np.log(np.maximum(r[m], 1))
    pp = np.polyfit(np.log(1 / eps[m]), lg, 1)
    r2p = 1 - ((lg - np.polyval(pp, np.log(1 / eps[m]))) ** 2).sum() / ((lg - lg.mean()) ** 2).sum()
    return ("ALG" if r2p > r2l else "EXP"), float(r2l), float(r2p)


def synth_field(T, P, alpha, noise_frac, seed):
    """指数谱 + 噪声地板：lambda_k = exp(-alpha k) + noise_frac。"""
    r = np.random.default_rng(seed)
    k = np.arange(1, P + 1)
    lam = np.exp(-alpha * k) + noise_frac
    sig = np.sqrt(lam)
    # 生成相关样本：白噪声乘以 sigma（等价于对角协方差）
    X = r.standard_normal((T, P)) * sig[None, :]
    return X


def measure(X):
    Y = X - X.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    lam = (sv ** 2) / (Y.shape[0] - 1)
    sc, r2e, r2a = spectrum_fits(lam)
    rc, r2l, r2p = rank_fits(lam)
    return sc, rc, (sc == rc), r2e, r2a, r2l, r2p


print("=" * 108)
print("有限样本基线：合成「指数谱 + 噪声地板」的一致性检验")
print("=" * 108)

CASES = [
    # (T, P, alpha, noise_frac, label)  — T, P 与观测数据匹配
    (1879, 500, 0.010, 0.0,    "HadISST1 规模, 无噪声"),
    (1879, 500, 0.010, 1e-4,   "HadISST1 规模, 噪声 1e-4"),
    (1879, 500, 0.005, 1e-3,   "HadISST1 规模, 噪声 1e-3"),
    (494,  500, 0.010, 0.0,    "OISSTv2 规模, 无噪声"),
    (494,  500, 0.010, 1e-3,   "OISSTv2 规模, 噪声 1e-3"),
    (494,  500, 0.020, 1e-3,   "OISSTv2 规模, α=0.02, 噪声 1e-3"),
    (494,  800, 0.010, 1e-3,   "OISSTv2 规模, P=800, 噪声 1e-3"),
]
results = {}
for T, P, alpha, nf, lab in CASES:
    agrees, scs, rcs, gaps = [], [], [], []
    for s in range(20):
        X = synth_field(T, P, alpha, nf, 1000 + s)
        sc, rc, ag, r2e, r2a, r2l, r2p = measure(X)
        agrees.append(ag); scs.append(sc); rcs.append(rc)
        gaps.append(abs(r2e - r2a))
    a = float(np.mean(agrees))
    results[lab] = dict(T=T, P=P, alpha=alpha, noise=nf,
                        agree_rate=a, n_trials=20,
                        spec_class_counts={"EXP": scs.count("EXP"), "ALG": scs.count("ALG")},
                        rank_class_counts={"EXP": rcs.count("EXP"), "ALG": rcs.count("ALG")},
                        median_spec_gap=float(np.median(gaps)))
    print(f"  {lab:<30} T={T:>5} P={P:>4}  一致率={a*100:>5.0f}%  "
          f"谱类 EXP×{scs.count('EXP'):>2}/ALG×{scs.count('ALG'):<2}  "
          f"秩类 EXP×{rcs.count('EXP'):>2}/ALG×{rcs.count('ALG'):<2}  "
          f"|gap|中位={np.median(gaps):.4f}")

print()
print("=" * 108)
print("结论")
print("=" * 108)
print("  · 若合成干净指数谱的一致率接近 100%，则观测数据的低一致率是有信息量的。")
print("  · 若合成含噪声的一致率也明显低于 100%，则观测数据的失败**部分是有限样本效应**。")
obs = 4 / 14
base = [v["agree_rate"] for v in results.values()]
print(f"  观测数据一致率: {obs*100:.0f}% (4/14)")
print(f"  合成基线一致率: {min(base)*100:.0f}% – {max(base)*100:.0f}%")
json.dump(dict(observed_agree_rate=obs, synthetic_baselines=results),
          io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"  已保存 {OUT}")
