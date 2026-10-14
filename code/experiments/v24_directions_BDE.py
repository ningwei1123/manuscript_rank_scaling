# -*- coding: utf-8 -*-
"""方向 B 收尾 + 方向 D + 方向 E（合并验证）。

方向 B 结论：范数界（Davis-Kahan 型）成立但松；一阶修正不适用。
方向 D：相关函数指数衰减 => 协方差谱不慢于指数（代数分支的不可行判据）
方向 E：样本量律 r*(M) = (1/alpha) log M + c 的严格化
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v24_BDE.json"
res = {}

# ============ 方向 B：范数界的成立性 ============
print("=" * 112)
print("方向 B 收尾： Davis-Kahan 型范数界 |T_out - T_in| <= r ||E||_2 是否成立？")
print("=" * 112)
rng = np.random.default_rng(5)
print(f"  {'n':>5}{'alpha':>7}{'r':>4}{'mis':>7}{'|超出|':>12}{'r||E||':>12}{'界成立?':>9}{'紧度':>9}")
Brows = []
for n, alpha, r in ((60, 0.15, 10), (80, 0.05, 15), (60, 0.4, 10)):
    lam = np.exp(-alpha * np.arange(1, n + 1))
    C = np.diag(lam)
    for mis in (0.005, 0.02, 0.1, 0.3):
        Qb, _ = np.linalg.qr(np.random.default_rng(13).standard_normal((n, n)))
        A = Qb + mis * np.random.default_rng(13).standard_normal((n, n)) / np.sqrt(n)
        Cy = A @ C @ A.T
        w_in = np.sort(lam)[::-1]; w_out = np.sort(np.linalg.eigvalsh(Cy))[::-1]
        T_in = float(w_in[r:].sum()); T_out = float(w_out[r:].sum())
        E = Cy - C
        nE = float(np.linalg.norm(E, 2))
        bnd = r * nE
        excess = abs(T_out - T_in)
        ok = excess <= bnd + 1e-9
        Brows.append(dict(n=n, alpha=alpha, r=r, mis=mis, excess=excess,
                          bound=bnd, ok=bool(ok),
                          tight=bnd / max(excess, 1e-30)))
        print(f"  {n:>5}{alpha:>7.2f}{r:>4}{mis:>7.3f}{excess:>12.4e}{bnd:>12.4e}"
              f"{('Y' if ok else 'N'):>9}{bnd/max(excess,1e-30):>9.2f}")
res["B_norm_bound"] = Brows
tight = [b["tight"] for b in Brows]
print(f"\n  界全部成立: {all(b['ok'] for b in Brows)}")
print(f"  紧度（界/超出）范围: {min(tight):.2f} .. {max(tight):.2f}（越大越松）")

# ============ 方向 D：相关函数衰减 -> 协方差谱 ============
print()
print("=" * 112)
print("方向 D：相关函数指数衰减 => 协方差谱不慢于指数？（Abel / Toeplitz 检验）")
print("=" * 112)
print("""
  论据（解析）：
    设 R(t) = <f, U^t f>。若 |R(t)| <= K a^t（a < 1，指数衰减），则自协方差序列
    是几何衰减的。对由此构造的 Toeplitz 协方差矩阵 C_M（阶 M），
    其特征值 lam_k(C_M) 的衰减由 R 的**谱密度**（Fejer/Riesz）决定：
    若 R 几何衰减，则谱密度是**解析**的（Wiener 类），
    对应 lam_k 至少指数衰减（解析函数的 Fourier 系数）。
    故 lam_k 不能是 k^{-beta} 形式（代数）——代数是更慢的衰减。

  数值检验：比较 (i) 几何衰减 R 生成的 Toeplitz 谱，(ii) 代数衰减 R 生成的谱。
""")
Ms = (16, 32, 64, 128)
for name, decay in (("几何 a=0.5", lambda t: 0.5 ** t),
                    ("几何 a=0.9", lambda t: 0.9 ** t),
                    ("代数 t^-1.5", lambda t: (t + 1.0) ** -1.5),
                    ("代数 t^-0.5", lambda t: (t + 1.0) ** -0.5)):
    print(f"\n  --- R(t) = {name} ---")
    print(f"  {'M':>6}{'lam_1':>11}{'lam_2/lam_1':>13}{'截面 (log-log 斜率)':>21}")
    for M in Ms:
        t = np.arange(M)
        R = decay(t)
        C = np.array([[R[abs(i - j)] for j in range(M)] for i in range(M)])
        w = np.sort(np.linalg.eigvalsh(C))[::-1]
        w = np.maximum(w, 1e-300)
        k = np.arange(1, M + 1)
        m = k >= 3
        sl = np.polyfit(np.log(k[m]), np.log(w[m]), 1)[0]
        print(f"  {M:>6}{w[0]:>11.4e}{w[1]/w[0] if w[0]>0 else 0:>13.6f}{-sl:>21.4f}")
    print(f"     （log-log 斜率接近 0 => 指数衰减；接近正常数 => 代数衰减）")

# ============ 方向 E：样本量律 ============
print()
print("=" * 112)
print("方向 E：样本量律 r*(M) = (1/alpha) log M + c 的检验")
print("=" * 112)
print("  定义 r*(M) = argmin_r [ 尾部能量(r) + r/M ]（偏差-方差权衡）")
print("  理论：尾部能量 ~ e^{-2 alpha r}，平衡 e^{-2 alpha r} ~ r/M => r* ~ (1/(2alpha)) log M")
print()
for alpha in (0.05, 0.1, 0.2, 0.4):
    n = 400
    lam = np.exp(-alpha * np.arange(1, n + 1))
    lam = lam / lam.sum()
    Ms = (100, 300, 1000, 3000, 10000, 30000, 100000)
    rs = []
    for M in Ms:
        tail = 1 - np.cumsum(lam)
        obj = tail + np.arange(1, n + 1) / M
        rs.append(int(np.argmin(obj) + 1))
    rs = np.array(rs, float)
    lgM = np.log(Ms)
    sl = np.polyfit(lgM, rs, 1)
    pred = 1 / (2 * alpha)
    print(f"  alpha={alpha:<5}  斜率={sl[0]:>8.4f}  理论 1/(2alpha)={pred:>8.4f}"
          f"  比={sl[0]/pred:>7.4f}  R²={1-((rs-np.polyval(sl,lgM))**2).sum()/((rs-rs.mean())**2).sum():>8.4f}")

res["D_and_E_note"] = "见上方输出"
json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
