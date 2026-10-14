# -*- coding: utf-8 -*-
"""确认正确的闭式形式，并量化对稿件数值结论的影响。

闭式族（用 e^{-2 a r} <= K * eps^2 的 K 形式参数化）：
  K = 1/(1-e^{-2an})              -> 稿件形式     r = (1/2a)ln[(1-e^{-2an})/(eps^2 ... )] ...
  逐项推导，找出与穷举**完全吻合**的单参数形式。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v16_closed_form_final.json"


def rank_exact(alpha, n, eps):
    l2 = np.exp(-2 * alpha * np.arange(n))
    tot = l2.sum()
    for r in range(n + 1):
        if l2[r:].sum() <= eps ** 2 * tot:
            return r
    return n


CANDIDATES = {
    # 稿件印出
    "manuscript": lambda a, n, e: (1 / (2 * a)) * np.log(
        (1 - np.exp(-2 * a * n)) / (e ** 2 * (1 - np.exp(-2 * a)))) + 1,
    # 去 +1
    "no_plus1": lambda a, n, e: (1 / (2 * a)) * np.log(
        (1 - np.exp(-2 * a * n)) / (e ** 2 * (1 - np.exp(-2 * a)))),
    # 去分母（我诊断给出的「正确推导」）
    "no_denom": lambda a, n, e: -(1 / (2 * a)) * np.log(
        e ** 2 * (1 - np.exp(-2 * a * n))),
    # 无穷 n 极限形式
    "inf_n": lambda a, n, e: (1 / (2 * a)) * np.log(
        1.0 / (e ** 2 * (1 - np.exp(-2 * a)))) + 1,
    # 教科书 KL 形式（无分母修正）
    "kl_naive": lambda a, n, e: (1 / (2 * a)) * np.log(1.0 / e ** 2),
}

print("=" * 116)
print("候选闭式的系统对照（70 组）")
print("=" * 116)
print(f"  {'alpha':>7}{'n':>8}{'eps':>9}{'穷举':>8}"
      + "".join(f"{k:>14}" for k in CANDIDATES))
rows = []
for alpha in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5):
    for n in (2000, 20000):
        for eps in (0.3, 0.1, 0.03, 0.01, 0.001):
            re_ = rank_exact(alpha, n, eps)
            vals = {k: float(f(alpha, n, eps)) for k, f in CANDIDATES.items()}
            rec = dict(alpha=alpha, n=n, eps=eps, r_exact=int(re_), **vals)
            rows.append(rec)

# 汇总统计
print()
print("=" * 116)
print("各候选形式的偏差统计（对 70 组）")
print("=" * 116)
print(f"  {'形式':>14}{'偏差中位':>11}{'偏差最大':>11}{'偏差最小':>11}"
      f"{'|偏差|<1.5 组数':>18}{'相对误差中位':>14}")
best = None
for k in CANDIDATES:
    d = np.array([r[k] - r["r_exact"] for r in rows])
    rel = np.array([(r[k] - r["r_exact"]) / max(r["r_exact"], 1) * 100 for r in rows])
    good = int((np.abs(d) < 1.5).sum())
    print(f"  {k:>14}{np.median(d):>11.3f}{d.max():>11.3f}{d.min():>11.3f}"
          f"{good:>13}/{len(rows):<4}{np.median(rel):>13.1f}%")
    if best is None or good > best[1]:
        best = (k, good)
print(f"\n  => 最吻合穷举的形式: **{best[0]}**（{best[1]}/{len(rows)} 组偏差 < 1.5）")

json.dump(dict(rows=rows, best=best[0]), io.open(OUT, "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
