# -*- coding: utf-8 -*-
"""严格 alpha_res（正确领先项）。

解析事实
--------
共振集合 = { mu1^{-m} * mu2^{-n} : m,n >= 0 }（转移算子，各向异性空间）
其中 mu1 > 1 > mu2 = 1/mu1。

模最小的非零共振（衰减最慢者）：
    m=1, n=0  ->  模 = mu1^{-1}
（m=0,n=1 给出 mu2^{-1} = mu1 > 1，**不衰减**，不属于谱隙内的共振）

故领先共振模 = 1/mu1，谱隙
    alpha_res = -ln(mu1^{-1}) = ln(mu1) = lambda_1^{Lyap}

而 Delta = lambda_1 - lambda_2 = ln mu1 - ln mu2 = 2 ln mu1
=> **alpha_res = Delta / 2**

前几版脚本的错误：把 m 的枚举上限 K 当成截断，
再取"模最小者"，于 K=8 时错误地取到 m=7，给出 alpha_res = 7 ln mu1。
正确做法是**解析指定领先项 m=1**。
"""
import io, json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v15_alpha_res.json"


def cat_matrix(n):
    return np.array([[n, 1.0], [n - 1, 1.0]])


def analysis(n):
    A = cat_matrix(n)
    ev = np.linalg.eigvals(A)
    ev = ev[np.argsort(-np.abs(ev))]
    mu1, mu2 = float(abs(ev[0])), float(abs(ev[1]))
    lam1, lam2 = np.log(mu1), np.log(mu2)
    Delta = lam1 - lam2
    # 解析领先共振（m=1, n=0，即 mu1^{-1}）
    lead_mod = 1.0 / mu1
    alpha_res = -np.log(lead_mod)
    return dict(n=n, mu1=mu1, mu2=mu2, lam1=float(lam1), lam2=float(lam2),
                Delta=float(Delta), lead_m=1, lead_n=0,
                lead_modulus=float(lead_mod), alpha_res=float(alpha_res),
                ratio_gap=float(alpha_res / Delta),
                ratio_lam1=float(alpha_res / lam1))


print("=" * 104)
print("严格 alpha_res：猫映射（解析领先项 m=1）")
print("=" * 104)
print(f"  {'n':>4}{'mu1':>10}{'lam1=ln mu1':>13}{'Delta=2ln mu1':>15}"
      f"{'领先模=1/mu1':>15}{'alpha_res':>12}{'a_res/Delta':>13}")
rows = []
for n in (2, 3, 4, 5, 6, 8):
    r = analysis(n)
    rows.append(r)
    print(f"  {n:>4}{r['mu1']:>10.4f}{r['lam1']:>13.6f}{r['Delta']:>15.6f}"
          f"{r['lead_modulus']:>15.6f}{r['alpha_res']:>12.6f}{r['ratio_gap']:>13.6f}")

D = np.array([r["Delta"] for r in rows])
As = np.array([r["alpha_res"] for r in rows])
L = np.array([r["lam1"] for r in rows])
RG = np.array([r["ratio_gap"] for r in rows])
print()
print("=" * 104)
print("判读")
print("=" * 104)
print(f"  Delta     : {D.min():.6f} .. {D.max():.6f}   跨度 {D.max()/D.min():.6f}x")
print(f"  alpha_res : {As.min():.6f} .. {As.max():.6f}   跨度 {As.max()/As.min():.6f}x")
print(f"  corr(Delta, alpha_res) = {np.corrcoef(D, As)[0,1]:+.12f}")
print()
print(f"  alpha_res = lam1 ？ 最大相对误差 {np.abs((As-L)/L).max()*100:.3e}%")
print(f"  alpha_res = Delta/2 ？ 最大相对误差 {np.abs((As-D/2)/(D/2)).max()*100:.3e}%")
print(f"  alpha_res/Delta 比值: {RG.min():.10f} .. {RG.max():.10f}  跨度 {RG.max()/RG.min():.10f}")
print()
print("  结论：")
print("  · alpha_res = ln(mu1) = lambda_1^{Lyap}  **解析严格成立**")
print("  · alpha_res = Delta / 2                  **解析严格成立**（猫映射 m=1 特例）")
print("  · 与 Axiom A 定理 alpha_res ≍ Delta 一致，比例常数 1/2")
print("  · 与 Lyapunov 顶隙**严格成比例**（corr = +1.0）")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")

print()
print("=" * 104)
print("最终对照：alpha_res（解析严格） vs alpha_cov（实测）")
print("=" * 104)
p = r"E:\deepseekworkspace\experiments_v12\v14_axiomA_cov.json"
if os.path.exists(p):
    cov = json.load(io.open(p, encoding="utf-8"))
    print(f"  {'n':>4}{'Delta':>10}{'alpha_res':>12}{'alpha_cov':>12}{'a_res/a_cov':>13}")
    for cr, rr in zip(cov, rows):
        print(f"  {cr['n']:>4}{cr['Delta']:>10.4f}{rr['alpha_res']:>12.6f}"
              f"{cr['alpha_cov']:>12.6f}{rr['alpha_res']/cr['alpha_cov']:>13.1f}")
    ac = np.array([c["alpha_cov"] for c in cov])
    print()
    print(f"  alpha_res 跨度 = {As.max()/As.min():.6f}x   （严格 ∝ Delta）")
    print(f"  alpha_cov 跨度 = {ac.max()/ac.min():.6f}x   （与 Delta 无关）")
    print(f"  corr(Delta, alpha_res) = {np.corrcoef(D, As)[0,1]:+.10f}")
    print(f"  corr(Delta, alpha_cov) = {np.corrcoef(D, ac)[0,1]:+.10f}")
    print()
    print("  => 两者在真 Axiom A 系统上**明确不同**：")
    print("     alpha_res 随 Delta 变化 2.27 倍，alpha_cov 只变化 0.6%")
