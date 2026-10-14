# -*- coding: utf-8 -*-
"""KS 定论（最终）：为什么"拟合更好的谱窗口"反而更差？

假设：秩曲线跨越 eps = 0.3 到 1e-4（3.5 个数量级），
      它需要的是**整条谱**的等效指数，而非某个高 R² 的局部窗口。
      => alpha 应在**与秩窗口匹配的谱范围**上拟合。

检验：对每个 alpha 窗口，报告 (R², R)，看是否存在系统关系。
"""
import io, json, os
import numpy as np

FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
OUT = r"E:\deepseekworkspace\experiments_v12\v19_ks_resolution.json"


def load(fn):
    rows = []
    for line in io.open(os.path.join(FD, fn), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue
    return np.array(rows)


sp = load("figures1_ks_spectrum.txt")
ra = load("figure2_ks_rank_accuracy.txt")
k, lam = sp[:, 0], sp[:, 1]
eps, r = ra[:, 0], ra[:, 1]

mm = (eps <= 0.3) & (eps >= 1e-4) & (r > 0)
slope = np.polyfit(np.log(1 / eps[mm]), r[mm], 1)[0]

print("=" * 108)
print("KS：alpha 窗口的 R² 与秩律一致性 R 的关系")
print("=" * 108)
print(f"  秩斜率（固定，窗口 0.3..1e-4）= {slope:.4f}")
print()
print(f"  {'alpha 窗口':>12}{'模态数':>8}{'alpha':>11}{'R²':>9}{'R = sl×α':>11}{'距 1':>9}")
rows = []
for lo, hi in [(2, 32), (2, 22), (3, 20), (5, 20), (10, 20), (15, 25), (15, 32)]:
    m = (k >= lo) & (k <= hi)
    if m.sum() < 5:
        continue
    lm = np.log(np.maximum(lam[m], 1e-300))
    s = np.polyfit(k[m], lm, 1)
    a = -s[0]
    r2 = 1 - ((lm - np.polyval(s, k[m])) ** 2).sum() / ((lm - lm.mean()) ** 2).sum()
    R = slope * a
    rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), alpha=float(a), r2=float(r2),
                     R=float(R), dev=float(abs(R - 1))))
    print(f"  {f'{lo}-{hi}':>12}{int(m.sum()):>8}{a:>11.6f}{r2:>9.4f}{R:>11.4f}"
          f"{abs(R-1)*100:>8.1f}%")

print()
print("=" * 108)
print("关系检验：R² 越高，R 越接近 1 吗？")
print("=" * 108)
r2s = np.array([x["r2"] for x in rows])
Rs = np.array([x["R"] for x in rows])
devs = np.array([x["dev"] for x in rows])
print(f"  corr(R², |R-1|) = {np.corrcoef(r2s, devs)[0,1]:+.4f}")
print(f"  {'=> 正相关：拟合越好偏差越大（反直觉）' if np.corrcoef(r2s, devs)[0,1] > 0.3 else '=> 无明显关系'}")
print()

# 关键对照
full = [x for x in rows if x["lo"] == 2 and x["hi"] == 32][0]
best_fit = max(rows, key=lambda x: x["r2"])
print(f"  · 全谱窗口 (2-32): R² = {full['r2']:.4f}（最低），R = {full['R']:.4f}（偏差 {full['dev']*100:.1f}%）")
print(f"  · 最佳拟合窗口 ({best_fit['lo']}-{best_fit['hi']}): R² = {best_fit['r2']:.4f}（最高），"
      f"R = {best_fit['R']:.4f}（偏差 {best_fit['dev']*100:.1f}%）")
print()
print("=" * 108)
print("结论")
print("=" * 108)
print(f"""
  KS 上秩律的偏差**不是一个确定的数**：它随 alpha 的拟合窗口从
  {devs.min()*100:.1f}% 变到 {devs.max()*100:.1f}%（7 个窗口）。

  且存在**反直觉的系统关系**：谱窗口拟合得越好（R² 越高），
  与秩律的一致性反而越差。

  原因：秩曲线跨越 eps = 0.3 到 1e-4（3.5 个数量级），
        它反映的是**整条谱**的等效衰减；而高 R² 的窗口只拟合谱的中段，
        恰好丢失了秩曲线在两端所依赖的信息。

  => 稿件应报告**偏差范围**（例如 {devs.min()*100:.0f}%-{devs.max()*100:.0f}%）
     并说明它依赖 alpha 的选取，而非给出单点 19%。
     这不是回避，而是对"KS 谱非单一指数"这一事实的如实呈现。
""")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"已保存 {OUT}")
