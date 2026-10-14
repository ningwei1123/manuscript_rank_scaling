# -*- coding: utf-8 -*-
"""第 3 项：Kuramoto–Sivashinsky 斜率 19% 偏差的诊断。

背景：稿件报告唯一的**独立检验**是 KS 的秩-精度斜率 vs 谱指数，二者差 19%。
这是审稿人最容易攻击的点。

诊断路径
--------
(a) 拟合窗口扫描：偏差是否只是窗口选择的产物？给出**范围**而非单点
(b) 混合谱形检验：KS 谱是纯指数、纯代数，还是混合（指数 + 代数尾巴）？
(c) 两-alpha 框架：用 v16 建立的 alpha_cov vs alpha_res 区分来解释

数据：从仓库的图数据读取 KS 谱（figures1_ks_spectrum.txt / figure2_ks_rank_accuracy.txt）
"""
import io, json, os
import numpy as np

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
OUT = r"E:\deepseekworkspace\experiments_v12\v18_ks_diagnosis.json"


def load_xy(fn, comment="#"):
    p = os.path.join(FD, fn)
    if not os.path.exists(p):
        return None
    rows = []
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith(comment):
            continue
        parts = line.split()
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            continue
    return np.array(rows) if rows else None


print("=" * 112)
print("第 3 项：KS 斜率偏差诊断")
print("=" * 112)

for fn in sorted(os.listdir(FD)):
    if "ks" in fn.lower():
        d = load_xy(fn)
        if d is not None:
            print(f"  {fn}: shape={d.shape}")
            print(f"     前 3 行: {d[:3].tolist()}")

print()
print("=" * 112)
print("(a) 拟合窗口扫描")
print("=" * 112)

sp = load_xy("figures1_ks_spectrum.txt")
ra = load_xy("figure2_ks_rank_accuracy.txt")
print(f"  KS 谱数据: {None if sp is None else sp.shape}")
print(f"  KS 秩-精度数据: {None if ra is None else ra.shape}")


def fit_power(x, y, skip=0):
    m = (x > 0) & (y > 0)
    x, y = x[m], y[m]
    if len(x) < 5:
        return None, None, 0
    s = np.polyfit(np.log(x[skip:]), np.log(y[skip:]), 1)
    r2 = 1 - ((np.log(y[skip:]) - np.polyval(s, np.log(x[skip:]))) ** 2).sum() / \
              ((np.log(y[skip:]) - np.log(y[skip:]).mean()) ** 2).sum()
    return float(s[0]), float(r2), len(x)


def fit_exp(x, y, skip=0):
    m = y > 0
    x, y = x[m], y[m]
    if len(x) < 5:
        return None, None, 0
    s = np.polyfit(x[skip:], np.log(y[skip:]), 1)
    r2 = 1 - ((np.log(y[skip:]) - np.polyval(s, x[skip:])) ** 2).sum() / \
              ((np.log(y[skip:]) - np.log(y[skip:]).mean()) ** 2).sum()
    return float(-s[0]), float(r2), len(x)


res = {}
if sp is not None and sp.shape[1] >= 2:
    k = sp[:, 0]; lam = sp[:, 1]
    print(f"  {'窗口起点':>10}{'代数指数':>12}{'R²_alg':>10}{'指数率':>12}{'R²_exp':>10}"
          f"{'判类':>7}")
    for skip in (0, 1, 2, 4, 8, 12):
        qa, r2a, n1 = fit_power(k, lam, skip)
        qe, r2e, n2 = fit_exp(k, lam, skip)
        if qa is None or qe is None:
            continue
        cls = "ALG" if r2a > r2e else "EXP"
        print(f"  {skip:>10}{qa:>12.4f}{r2a:>10.4f}{qe:>12.6f}{r2e:>10.4f}{cls:>7}")
        res[f"spec_skip{skip}"] = dict(q_alg=qa, r2_alg=r2a, q_exp=qe, r2_exp=r2e, cls=cls)

if ra is not None and ra.shape[1] >= 2:
    eps = ra[:, 0]; r = ra[:, 1]
    print()
    print(f"  KS 秩-精度：秩指数随窗口（eps 区间）的变化")
    print(f"  {'eps 窗口':>20}{'幂律指数':>12}{'R²_pow':>10}{'对数斜率':>12}{'R²_log':>10}")
    lo_hi = [(0.3, 1e-4), (0.3, 1e-2), (0.1, 1e-4), (0.1, 1e-3), (0.05, 1e-4), (0.5, 1e-6)]
    for lo, hi in lo_hi:
        m = (eps <= lo) & (eps >= hi) & (r > 0)
        if m.sum() < 5:
            continue
        x, y = np.log(1 / eps[m]), r[m]
        sp_ = np.polyfit(x, y, 1)
        r2l = 1 - ((y - np.polyval(sp_, x)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        xp, yp = np.log(1 / eps[m]), np.log(np.maximum(r[m], 1))
        pp = np.polyfit(xp, yp, 1)
        r2p = 1 - ((yp - np.polyval(pp, xp)) ** 2).sum() / ((yp - yp.mean()) ** 2).sum()
        print(f"  {f'{lo}..{hi}':>20}{pp[0]:>12.4f}{r2p:>10.4f}{sp_[0]:>12.4f}{r2l:>10.4f}")
        res[f"rank_{lo}_{hi}"] = dict(pow=float(pp[0]), r2_pow=float(r2p),
                                      log=float(sp_[0]), r2_log=float(r2l))

json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
