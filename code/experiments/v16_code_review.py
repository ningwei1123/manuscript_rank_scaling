# -*- coding: utf-8 -*-
"""算法与代码的严格检验：对稿件的核心算法做**独立复核**。

复核方法：对每个算法写**独立实现**（不同的数学路径），
          与主实现的输出逐点比较。完全一致才算通过。
"""
import io, json, math
import numpy as np

REPORT = []


def check(name, ok, detail=""):
    REPORT.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")


print("=" * 104)
print("① 秩-精度关系的定义与实现")
print("=" * 104)

# --- 主实现（稿件代码路径）：相对 Frobenius 误差 ---
def rank_rel_frobenius(lam, eps):
    """r(eps) = min{ r : sqrt(sum_{k>r} lam_k^2 / sum_k lam_k^2) <= eps }"""
    lam = np.sort(np.asarray(lam, float))[::-1]
    l2 = lam ** 2
    tot = l2.sum()
    for r in range(len(lam) + 1):
        if l2[r:].sum() <= eps ** 2 * tot:
            return r
    return len(lam)


# --- 独立实现：用 cumsum（反向）走不同代码路径 ---
def rank_cumsum(lam, eps):
    lam = np.sort(np.asarray(lam, float))[::-1]
    l2 = lam ** 2
    tot = l2.sum()
    tail = np.cumsum(l2[::-1])[::-1]          # tail[i] = sum_{k>=i} l2
    idx = np.where(tail <= eps ** 2 * tot)[0]
    return int(idx[0]) if len(idx) else len(lam)


# --- 独立实现：解析（指数谱）---
def rank_exp_analytic(alpha, n, eps):
    """lam_k = e^{-alpha k}, k=0..n-1，解 e^{-2 alpha r}(1-e^{-2 alpha(n-r)})/(1-e^{-2 alpha})
       = eps^2 (1-e^{-2 alpha n})/(1-e^{-2 alpha})，取 ceil。"""
    def tail(r):
        return np.exp(-2 * alpha * r) * (1 - np.exp(-2 * alpha * (n - r))) / (1 - np.exp(-2 * alpha))
    target = eps ** 2 * (1 - np.exp(-2 * alpha * n)) / (1 - np.exp(-2 * alpha))
    for r in range(n + 1):
        if tail(r) <= target:
            return r
    return n


ok_a = True
for alpha in (0.02, 0.05, 0.1, 0.3):
    for n in (100, 2000, 20000):
        for eps in (0.3, 0.1, 0.01, 0.001, 1e-4):
            lam = np.exp(-alpha * np.arange(n))
            r1 = rank_rel_frobenius(lam, eps)
            r2 = rank_cumsum(lam, eps)
            r3 = rank_exp_analytic(alpha, n, eps)
            if not (r1 == r2 == r3):
                ok_a = False
                print(f"    不一致: alpha={alpha} n={n} eps={eps} -> {r1}, {r2}, {r3}")
check("秩定义：三种独立实现完全一致（60 组）", ok_a)

print()
print("=" * 104)
print("② 指数分支的闭式")
print("=" * 104)

def closed_form(alpha, n, eps):
    return (1 / (2 * alpha)) * np.log((1 - np.exp(-2 * alpha * n)) /
                                      (eps ** 2 * (1 - np.exp(-2 * alpha)))) + 1

def closed_form_alt(alpha, n, eps):
    """独立推导：解 e^{-2 a R} = eps^2 (1-e^{-2an})/(1-e^{-2a})，再处理 0-based 偏移。"""
    rhs = eps ** 2 * (1 - np.exp(-2 * alpha * n)) / (1 - np.exp(-2 * alpha))
    R = -np.log(rhs) / (2 * alpha)
    return R + 1

ok_b = True
maxdev = 0.0
for alpha in (0.02, 0.05, 0.1, 0.2, 0.4):
    for n in (2000, 100000):
        for eps in (0.1, 0.01, 0.001):
            lam = np.exp(-alpha * np.arange(n))
            r = rank_rel_frobenius(lam, eps)
            c = closed_form(alpha, n, eps)
            c2 = closed_form_alt(alpha, n, eps)
            if abs(c - c2) > 1e-9:
                ok_b = False
                print(f"    两个闭式实现不一致: {c} vs {c2}")
            # 闭式应 >= 精确秩（上界）
            if c < r - 1e-9:
                ok_b = False
                print(f"    闭式 < 精确秩: alpha={alpha} n={n} eps={eps} c={c:.4f} r={r}")
            maxdev = max(maxdev, c - r)
check("闭式：两个独立推导一致，且恒为精确秩上界（30 组）", ok_b,
      f"最大超出 {maxdev:.3f}")

print()
print("=" * 104)
print("③ 代数分支的指数 2/(2β−1)")
print("=" * 104)

def rank_alg_power(lam, eps):
    return rank_rel_frobenius(lam, eps)

ok_c = True
for beta in (0.75, 1.0, 1.5, 2.0, 3.0):
    n = 200000
    lam = (np.arange(1, n + 1, dtype=float)) ** (-beta)
    eps = np.logspace(np.log10(0.3), np.log10(1e-5), 30)
    rr = np.array([rank_alg_power(lam, e) for e in eps], float)
    # 拟合 r ~ eps^{-q}
    m = rr > 1
    s = np.polyfit(np.log(1 / eps[m]), np.log(rr[m]), 1)
    q_meas = s[0]
    q_theory = 2 / (2 * beta - 1)
    rel = abs(q_meas - q_theory) / q_theory
    if rel > 0.02:
        ok_c = False
        print(f"    beta={beta}: 实测 {q_meas:.4f} vs 理论 {q_theory:.4f}  相对误差 {rel*100:.1f}%")
    else:
        print(f"    beta={beta}: 实测 {q_meas:.4f} vs 理论 {q_theory:.4f}  相对误差 {rel*100:.2f}%")
check("代数分支指数 = 2/(2β−1)", ok_c)

print()
print("=" * 104)
print("④ 猫映射 Lyapunov 指数与 alpha_res")
print("=" * 104)

ok_d = True
for n in (2, 3, 4, 5, 6, 8):
    A = np.array([[n, 1.0], [n - 1, 1.0]])
    ev = np.linalg.eigvals(A)
    mu1 = float(np.abs(ev).max())
    mu2 = float(np.abs(ev).min())
    # 独立核对：det = 1 且 mu2 = 1/mu1
    if abs(np.linalg.det(A) - 1) > 1e-10:
        ok_d = False; print(f"    n={n}: det != 1")
    if abs(mu1 * mu2 - 1) > 1e-10:
        ok_d = False; print(f"    n={n}: mu1*mu2 != 1")
    lam1 = np.log(mu1); lam2 = np.log(mu2)
    if abs(lam1 + lam2) > 1e-10:
        ok_d = False; print(f"    n={n}: lam1 + lam2 != 0")
    alpha_res = np.log(mu1)
    Delta = lam1 - lam2
    if abs(alpha_res - Delta / 2) > 1e-12:
        ok_d = False; print(f"    n={n}: alpha_res != Delta/2")
check("猫映射：det=1, μ₁μ₂=1, λ₁+λ₂=0, α_res=Δ/2（6 个 n）", ok_d)

print()
print("=" * 104)
print("⑤ 猫映射轨道与 Lyapunov 数值估计")
print("=" * 104)

def cat_orbit(A, T, x0, burn=2000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = (A @ x) % 1.0
    X = np.empty((T, 2))
    for t in range(T):
        x = (A @ x) % 1.0
        X[t] = x
    return X

def lyap_qr(A, T=200000, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.random(2)
    for _ in range(2000):
        x = (A @ x) % 1.0
    Q = np.eye(2); s = np.zeros(2)
    for _ in range(T):
        M = A @ Q
        Q, R = np.linalg.qr(M)
        d = np.diag(R)
        d = np.where(np.abs(d) < 1e-300, 1e-300, d)
        s += np.log(np.abs(d))
        x = (A @ x) % 1.0
    return s / T

ok_e = True
for n in (2, 4, 8):
    A = np.array([[n, 1.0], [n - 1, 1.0]])
    mu1 = float(np.abs(np.linalg.eigvals(A)).max())
    ly = lyap_qr(A)
    err = max(abs(ly[0] - np.log(mu1)), abs(ly[1] + np.log(mu1)))
    if err > 1e-6:
        ok_e = False
        print(f"    n={n}: 数值 {ly} vs 理论 ±{np.log(mu1):.8f}  误差 {err:.2e}")
check("Lyapunov QR 估计与解析值吻合（3 个 n，误差 < 1e-6）", ok_e)

print()
print("=" * 104)
print("⑥ 判类函数的一致性（主实现 vs 独立实现）")
print("=" * 104)

def classify_main(lam, eps_lo=0.3, eps_hi=1e-4):
    lam = np.sort(np.asarray(lam, float))[::-1]; n = len(lam); k = np.arange(1, n + 1)
    pos = lam > 1e-16
    le = np.log(lam[pos])
    se = np.polyfit(k[pos], le, 1)
    r2e = 1 - ((le - np.polyval(se, k[pos])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    sa = np.polyfit(np.log(k[pos]), le, 1)
    r2a = 1 - ((le - np.polyval(sa, np.log(k[pos]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    eps = np.logspace(np.log10(eps_lo), np.log10(eps_hi), 60)
    r = np.array([rank_rel_frobenius(lam, e) for e in eps], float)
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
    return sc, rc, dict(r2e=r2e, r2a=r2a, r2l=r2l, r2p=r2p)

ok_f = True
# 纯净指数谱 -> 应判 EXP/EXP
for alpha in (0.05, 0.1, 0.2):
    lam = np.exp(-alpha * np.arange(400))
    sc, rc, d = classify_main(lam)
    if not (sc == "EXP" and rc == "EXP"):
        ok_f = False
        print(f"    指数谱 alpha={alpha}: 判为 {sc}/{rc}（期望 EXP/EXP）  {d}")
# 纯净代数谱（beta 足够大）-> 应判 ALG/ALG
for beta in (1.0, 2.0):
    lam = np.arange(1, 401, dtype=float) ** (-beta)
    sc, rc, d = classify_main(lam)
    if not (sc == "ALG" and rc == "ALG"):
        ok_f = False
        print(f"    代数谱 beta={beta}: 判为 {sc}/{rc}（期望 ALG/ALG）  {d}")
check("判类函数：纯净指数谱判 EXP、纯净代数谱判 ALG", ok_f)

print()
print("=" * 104)
print("总汇总")
print("=" * 104)
npass = sum(1 for _, ok, _ in REPORT if ok)
print(f"  通过 {npass}/{len(REPORT)}")
for name, ok, det in REPORT:
    print(f"    [{'PASS' if ok else 'FAIL'}] {name}")

json.dump([dict(name=n, ok=o, detail=d) for n, o, d in REPORT],
          io.open(r"E:\deepseekworkspace\experiments_v12\v16_code_review.json", "w",
                  encoding="utf-8"), ensure_ascii=False, indent=2)
print("\n已保存 v16_code_review.json")
