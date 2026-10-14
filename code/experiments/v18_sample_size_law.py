# -*- coding: utf-8 -*-
"""第 4 项定稿：确认斜率因子 2 的来源，给出正确的律。

观察：实测斜率 ≈ 2 × 1/(2α) = 1/α。
假设：正确的律是 r*(M) = (1/α) log M + c，而非 (1/2α) log M。

理由（推导）：r*(M) 由 B(r) = V(r,M) 平衡。
  B(r) = Σ_{k>r} λ_k ≈ λ_r/(1-e^{-α}) ~ e^{-αr}/(1-e^{-α})
  V(r,M) = c r / M
  平衡：e^{-αr}/(1-e^{-α}) = c r/M
       => αr = log M - log r + log(c/(1-e^{-α}))
       => r* = (1/α) log M - (1/α) log r + const
  一次迭代给出 r* = (1/α) log M + O(log log M)。
  **系数是 1/α，不是 1/(2α)。**

（1/(2α) 出现在 **B(r)=ε²** 的秩-精度关系中，因为那里比较的是 L2 范数平方。
 而样本量律比较的是**平均**偏差与方差，故系数为 1/α。）
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v18_sample_law_final.json"


def spectrum(kind, param, n):
    return (np.exp(-param * np.arange(1, n + 1)) if kind == "exp"
            else np.arange(1, n + 1, dtype=float) ** (-param))


def r_star(lam, M, c=1.0):
    n = len(lam)
    B = np.cumsum(lam[::-1])[::-1]      # B[r-1] = sum_{k>=r} lam
    B = np.concatenate([B, [0.0]])
    r_grid = np.arange(1, n + 1)
    errs = B[r_grid - 1] + c * r_grid / M
    i = int(np.argmin(errs))
    return int(r_grid[i]), float(errs[i])


print("=" * 108)
print("确认：r*(M) 的斜率是 1/α 还是 1/(2α)？")
print("=" * 108)
print(f"  {'谱':>12}{'n':>5}{'alpha':>9}{'1/alpha':>10}{'实测斜率':>11}"
      f"{'斜率/(1/alpha)':>16}{'R²':>9}")
rows = []
for kind, param in (("exp", 0.05), ("exp", 0.1), ("exp", 0.2), ("exp", 0.4), ("exp", 0.6)):
    for n in (300, 800):
        lam = spectrum(kind, param, n)
        # 只在未饱和的 M 范围内拟合（r* < 0.8n）
        Ms, rs = [], []
        for M in np.logspace(np.log10(50), np.log10(1e7), 200):
            r, _ = r_star(lam, int(M))
            if r < 0.8 * n:
                Ms.append(M); rs.append(r)
        if len(Ms) < 8:
            continue
        Ms = np.array(Ms); rs = np.array(rs, float)
        s = np.polyfit(np.log(Ms), rs, 1)
        r2 = 1 - ((rs - np.polyval(s, np.log(Ms))) ** 2).sum() / ((rs - rs.mean()) ** 2).sum()
        a = param
        rows.append(dict(kind=kind, param=param, n=n, alpha=a, slope=float(s[0]),
                         ratio_to_1_a=float(s[0] * a), r2=float(r2)))
        print(f"  {kind+' '+str(param):>12}{n:>5}{a:>9.4f}{1/a:>10.3f}{s[0]:>11.4f}"
              f"{s[0]*a:>16.4f}{r2:>9.4f}")

rt = np.array([r["ratio_to_1_a"] for r in rows])
print()
print(f"  斜率 × alpha 的比（应为 1.0 若斜率 = 1/alpha）: "
      f"中位 {np.median(rt):.4f}  范围 {rt.min():.4f} .. {rt.max():.4f}")
print(f"  => {'确认斜率 = 1/alpha' if abs(np.median(rt)-1) < 0.1 else '未确认'}")

print()
print("=" * 108)
print("外推公式：r*(M) = (1/alpha) log M + c  的预测能力")
print("=" * 108)
print(f"  {'谱':>12}{'M0':>9}{'预测 r*(4M0)':>15}{'实测':>9}{'相对误差':>11}")
ext = []
for kind, param in (("exp", 0.05), ("exp", 0.1), ("exp", 0.2)):
    n = 800
    lam = spectrum(kind, param, n)
    for M0 in (100, 1000, 10000):
        Ms = np.logspace(np.log10(50), np.log10(M0), 30)
        rs = np.array([r_star(lam, int(M))[0] for M in Ms], float)
        s = np.polyfit(np.log(Ms), rs, 1)
        pred = np.polyval(s, np.log(4 * M0))
        actual = r_star(lam, 4 * M0)[0]
        rel = (pred - actual) / actual * 100
        ext.append(dict(kind=kind, param=param, M0=M0, pred=float(pred),
                        actual=int(actual), rel_pct=float(rel)))
        print(f"  {kind+' '+str(param):>12}{M0:>9}{pred:>15.2f}{actual:>9}{rel:>10.1f}%")

print()
print("=" * 108)
print("适用域（修正）：M 需要多大才能让 r* 达到给定比例？")
print("=" * 108)
print(f"  {'谱':>12}{'alpha':>9}{'M(r*=0.5n)':>14}{'M(r*=0.9n)':>14}")
for kind, param in (("exp", 0.05), ("exp", 0.1), ("exp", 0.2), ("exp", 0.4)):
    n = 800
    lam = spectrum(kind, param, n)
    Ms = np.logspace(np.log10(50), np.log10(1e9), 400)
    r05 = r09 = None
    for M in Ms:
        r, _ = r_star(lam, int(M))
        if r05 is None and r >= 0.5 * n:
            r05 = int(M)
        if r09 is None and r >= 0.9 * n:
            r09 = int(M)
        if r05 and r09:
            break
    print(f"  {kind+' '+str(param):>12}{param:>9.4f}"
          f"{(f'{r05:.2e}' if r05 else '>1e9'):>14}{(f'{r09:.2e}' if r09 else '>1e9'):>14}")

json.dump(dict(slopes=rows, extrapolation=ext),
          io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
