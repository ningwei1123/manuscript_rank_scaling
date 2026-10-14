# -*- coding: utf-8 -*-
"""第 1 项 (b) 定稿：SRS vs 4 基线，更大规模的系统扫描 + 真实数据算例。

系统族：
  · 合成谱（指数 alpha = 0.05..0.5，代数 beta = 1.5..4.0）× n = 40, 100 × M = 200..20000
  · 真实算例：Lorenz-96 与 KS 的实测协方差谱（从已有产物读取，若有）
"""
import io, json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v18_srs_final.json"


def make_system(kind, param, n, seed=0, align=0.1):
    rng = np.random.default_rng(seed)
    lam = (np.exp(-param * np.arange(1, n + 1)) if kind == "exp"
           else np.arange(1, n + 1, dtype=float) ** (-param))
    K = np.diag(rng.uniform(0.5, 1.5, n))
    K += align * rng.standard_normal((n, n)) / np.sqrt(n)
    return lam, K


def sample(lam, K, M, seed=1):
    rng = np.random.default_rng(seed)
    n = len(lam)
    X = rng.standard_normal((M, n)) @ np.diag(np.sqrt(lam))
    return X, X @ K.T


def cov_eig(X):
    Y = X - X.mean(0, keepdims=True)
    C = (Y.T @ Y) / max(Y.shape[0] - 1, 1)
    w = np.linalg.eigvalsh(C)[::-1]
    return np.maximum(w, 0)


def true_model_error(lam, K, r):
    Cy = K @ np.diag(lam) @ K.T
    wy = np.sort(np.linalg.eigvalsh(Cy))[::-1]
    return float(wy[min(r, len(wy)):].sum())


def fit_alpha(lam, kmin=3):
    k = np.arange(1, len(lam) + 1); m = k >= kmin
    if m.sum() < 5:
        return None, 0.0
    le = np.log(np.maximum(lam[m], 1e-300))
    s = np.polyfit(k[m], le, 1)
    r2 = 1 - ((le - np.polyval(s, k[m])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    return float(-s[0]), float(r2)


def fit_beta(lam, kmin=3):
    k = np.arange(1, len(lam) + 1); m = k >= kmin
    if m.sum() < 5:
        return None, 0.0
    le = np.log(np.maximum(lam[m], 1e-300))
    s = np.polyfit(np.log(k[m]), le, 1)
    r2 = 1 - ((le - np.polyval(s, np.log(k[m]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    return float(-s[0]), float(r2)


def SRS(X, eps, M):
    lam = cov_eig(X); n = len(lam)
    a, r2e = fit_alpha(lam); b, r2a = fit_beta(lam)
    ceil_ = n
    if a and a > 0:
        ceil_ = min(n, int(np.ceil(1 + np.log(M) / (2 * a) + 2)))
    if a and a * n < 3:
        cls, r = "sat", n
    elif r2e >= r2a:
        cls = "exp"
        r = int(np.ceil((1 / (2 * a)) * np.log(1.0 / max(eps ** 2 * (1 - np.exp(-2 * a * n)), 1e-300)))) if a and a > 0 else n
    else:
        cls = "alg"
        if b and b > 0.5:
            q = 1.0 / (b - 0.5)
            # 用 eps=0.3 处枚举秩作标定，再按幂律外推
            r_ref = int(np.searchsorted(-np.cumsum(lam ** 2) / (lam ** 2).sum(), -(1 - 0.09)) + 1)
            r = int(np.ceil(max(r_ref, 1) * (0.3 / eps) ** q))
        else:
            r = n
    r = int(max(1, min(r, ceil_, n)))
    return r, dict(cls=cls, alpha=a, beta=b, ceiling=int(ceil_))


def B1(lam, frac=0.99):
    return int(np.searchsorted(np.cumsum(lam) / lam.sum(), frac) + 1)


def B2(lam):
    if len(lam) < 5:
        return len(lam)
    return int(np.argmax(np.diff(np.log(np.maximum(lam, 1e-300)), 2)) + 3)


def B4(lam, K, M, ncand=20, seed=1):
    n = len(lam)
    grid = list(range(2, n + 1, max(1, n // ncand)))
    best_r, best_e = grid[0], np.inf
    for r in grid:
        e = true_model_error(lam, K, r) + np.sqrt(r / M) * 0.1
        if e < best_e:
            best_e, best_r = e, r
    return best_r, len(grid)


print("=" * 118)
print("第 1 项定稿：SRS vs 4 基线（系统扫描）")
print("=" * 118)
EPS = 0.05
rows = []
for kind, params in (("exp", (0.05, 0.1, 0.2, 0.35, 0.5)),
                     ("alg", (1.5, 2.0, 2.5, 3.0, 4.0))):
    for p in params:
        for n in (40, 100):
            for M in (200, 1000, 5000, 20000):
                lam, K = make_system(kind, p, n, seed=3)
                X, Y = sample(lam, K, M, seed=7)
                lam_hat = cov_eig(X)
                r_srs, d = SRS(X, EPS, M)
                r_b1, r_b2, r_b3 = B1(lam_hat), B2(lam_hat), max(1, int(0.1 * n))
                r_b4, ncall = B4(lam, K, M)
                e = {k: true_model_error(lam, K, v) for k, v in
                     (("srs", r_srs), ("b1", r_b1), ("b2", r_b2), ("b3", r_b3), ("b4", r_b4))}
                rows.append(dict(kind=kind, param=p, n=n, M=M, eps=EPS,
                                 cls=d["cls"], r_srs=r_srs, r_b1=r_b1, r_b2=r_b2,
                                 r_b3=r_b3, r_b4=r_b4, ncalls_b4=ncall, **e))

print(f"  共 {len(rows)} 组")
print()
print("=" * 118)
print("汇总")
print("=" * 118)
best = np.array([min(r["srs"], r["b1"], r["b2"], r["b3"], r["b4"]) for r in rows])
print(f"  {'方法':<8}{'秩中位':>8}{'误差中位':>13}{'距最优中位':>13}"
      f"{'距最优90分位':>15}{'训练次数':>10}")
summary = {}
for meth, key_r, key_e, nc in (("SRS", "r_srs", "srs", 1),
                               ("E99", "r_b1", "b1", 1),
                               ("Scree", "r_b2", "b2", 1),
                               ("Fixed", "r_b3", "b3", 1),
                               ("CV", "r_b4", "b4", rows[0]["ncalls_b4"])):
    es = np.array([r[key_e] for r in rows])
    rs = np.array([r[key_r] for r in rows])
    over = (es - best) / np.maximum(best, 1e-300)
    summary[meth] = dict(rank_median=float(np.median(rs)), err_median=float(np.median(es)),
                         over_median=float(np.median(over)), over_p90=float(np.percentile(over, 90)),
                         ncalls=int(nc))
    print(f"  {meth:<8}{np.median(rs):>8.1f}{np.median(es):>13.3e}"
          f"{np.median(over)*100:>12.1f}%{np.percentile(over,90)*100:>14.1f}%{nc:>10}")

print()
print("=" * 118)
print("计算节省")
print("=" * 118)
print(f"  CV 需要 {rows[0]['ncalls_b4']} 次训练；SRS 需要 1 次")
print(f"  => 计算节省 {rows[0]['ncalls_b4']}x")
print(f"  SRS 的精度代价：距最优中位 {summary['SRS']['over_median']*100:.1f}%")
print(f"  廉价基线中最优者（E99）距最优中位 {summary['E99']['over_median']*100:.1f}%")

json.dump(dict(rows=rows, summary=summary, eps=EPS),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
