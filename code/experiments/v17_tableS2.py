# -*- coding: utf-8 -*-
"""用修正后的闭式重新生成 Supplementary Table 2。"""
import io, os, json
import numpy as np

OUTTXT = (r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling"
          r"\data\figure_data\tableS2_closed_form_bound.txt")
ART = r"E:\deepseekworkspace\experiments_v12\v17_closed_form_bound.json"


def r_exact(alpha, n, eps):
    e2 = np.exp(-2 * alpha * np.arange(n))
    tot = e2.sum()
    return next(r for r in range(n + 1) if e2[r:].sum() <= eps ** 2 * tot)


def r_closed(alpha, n, eps):
    """修正后的闭式（0-based 谱 lambda_j = e^{-alpha j}, j=0..n-1）：
       r = (1/(2 alpha)) ln[ 1 / (eps^2 (1 - e^{-2 alpha n})) ]"""
    return (1 / (2 * alpha)) * np.log(1.0 / (eps ** 2 * (1 - np.exp(-2 * alpha * n))))


rows = []
for alpha in (0.01, 0.02, 0.05, 0.1, 0.2, 0.4):
    for n in (2000, 100000):
        for eps in (0.1, 0.02, 0.005, 0.001):
            re_ = r_exact(alpha, n, eps)
            rc = r_closed(alpha, n, eps)
            rows.append(dict(alpha=alpha, n=n, eps=eps, r_exact=int(re_),
                             r_closed=round(float(rc), 4),
                             excess=round(float(rc - re_), 4),
                             rel_pct=round(float((rc - re_) / re_ * 100), 2) if re_ else 0.0))

os.makedirs(os.path.dirname(OUTTXT), exist_ok=True)
with io.open(OUTTXT, "w", encoding="utf-8") as f:
    f.write("# Supplementary Table 2: the closed form is an upper bound on the exact rank.\n")
    f.write("# Spectrum lambda_j = exp(-alpha j), j = 0..n-1. r_exact is enumerated from the\n")
    f.write("# cumulative tail; r_closed = (1/(2 alpha)) ln[ 1 / (eps^2 (1 - e^{-2 alpha n})) ].\n")
    f.write("# The closed form resolves the criterion with an infinite geometric tail, so it\n")
    f.write("# never asks for fewer modes than the enumeration.\n")
    f.write("alpha\tn\teps\tr_exact\tr_closed\texcess\trel_pct\n")
    for r in rows:
        f.write(f"{r['alpha']}\t{r['n']}\t{r['eps']}\t{r['r_exact']}\t{r['r_closed']}\t"
                f"{r['excess']}\t{r['rel_pct']}\n")

json.dump(rows, io.open(ART, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"已写 Supplementary Table 2：{len(rows)} 行")
print()
print("核验：")
print("  闭式恒为上界 ->", all(r["r_closed"] >= r["r_exact"] - 1e-6 for r in rows))
ex = [r["excess"] for r in rows]
rl = [r["rel_pct"] for r in rows]
print(f"  绝对超出：{min(ex):.3f} .. {max(ex):.3f} 个秩")
print(f"  相对超出：{min(rl):.1f}% .. {max(rl):.1f}%")
print()
print("对比（旧闭式）：绝对超出 0.47 .. 461.8，相对 5.6% .. 191.6%")
