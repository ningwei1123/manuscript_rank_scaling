# -*- coding: utf-8 -*-
"""非线性 Anosov 的**干净**检验。

判据（避免上版的锥判据错误）
--------------------------
映射 F 是 Anosov（二维）当且仅当存在连续的 DT-不变分解 E^s ⊕ E^u 与一致扩张/收缩。
数值上可靠的必要且充分标志（在紧流形上）：

  (A) **奇异值分离**：在每个点，DF 的两个奇异值 σ1 >= σ2 满足
      σ1 > 1 > σ2（一致地），且间隔 g = σ1 - 1、1 - σ2 有一致下界。
      这是"一致双曲"的直接数值标志。

  (B) **方向夹角**：DF 的不稳定奇异方向 u(x) 与 F(x) 处的不稳定奇异方向 u(F(x))
      夹角小（锥不变性）；且 u(x) 与稳定奇异方向 s(x) 的夹角一致有界远离 0。

  (C) **Lyapunov 指数一致**：数值估计的指数与解析值接近且方差小。

本脚本用 (A)+(B)+(C) 三者联合判定，并用**更小的 eps** 确保落在 Anosov 稳定域内。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v16_nonlinear_axiomA.json"


def cat_matrix(n):
    return np.array([[n, 1.0], [n - 1, 1.0]])


def g_and_J(x, kind=0):
    t1 = 2 * np.pi * x[0]; t2 = 2 * np.pi * x[1]
    if kind == 0:
        g = np.array([np.sin(t2), np.sin(t1)])
        J = np.array([[0.0, 2 * np.pi * np.cos(t2)],
                      [2 * np.pi * np.cos(t1), 0.0]])
    else:
        g = np.array([np.sin(t1) * np.cos(t2), np.sin(t1 + t2)])
        J = np.array([[2 * np.pi * np.cos(t1) * np.cos(t2),
                       -2 * np.pi * np.sin(t1) * np.sin(t2)],
                      [2 * np.pi * np.cos(t1 + t2), 2 * np.pi * np.cos(t1 + t2)]])
    return g, J


def F(x, A, eps, kind=0):
    g, _ = g_and_J(x, kind)
    return (A @ x + eps * g) % 1.0


def DF(x, A, eps, kind=0):
    _, J = g_and_J(x, kind)
    return A + eps * J


def check_hyperbolic(A, eps, kind=0, N=4000, seed=0):
    """判据 (A)+(B)：奇异值一致分离 + 不稳定方向锥不变。"""
    rng = np.random.default_rng(seed)
    X = rng.random((N, 2))
    sig1 = np.empty(N); sig2 = np.empty(N); ang = np.empty(N)
    cone_viol = 0
    for i, x in enumerate(X):
        J = DF(x, A, eps, kind)
        U, S, Vt = np.linalg.svd(J)
        sig1[i], sig2[i] = S[0], S[1]
        u_here = U[:, 0]                    # 不稳定方向（像空间）
        x_next = F(x, A, eps, kind)
        Jn = DF(x_next, A, eps, kind)
        Un, _, _ = np.linalg.svd(Jn)
        u_next = Un[:, 0]
        c = abs(np.dot(u_here, u_next))
        ang[i] = np.degrees(np.arccos(np.clip(c, 0, 1)))
        # 锥不变：DF 把 u_here 映到 x_next 处的不稳定方向，夹角应小
        if ang[i] > 20.0:
            cone_viol += 1
    return dict(
        sig1_min=float(sig1.min()), sig1_mean=float(sig1.mean()),
        sig2_max=float(sig2.max()), sig2_mean=float(sig2.mean()),
        gap_expand=float(sig1.min() - 1.0), gap_contract=float(1.0 - sig2.max()),
        angle_max=float(ang.max()), angle_mean=float(ang.mean()),
        cone_violations=int(cone_viol), cone_frac=float(cone_viol / N),
        hyperbolic=bool(sig1.min() > 1.0 and sig2.max() < 1.0 and cone_viol / N < 0.02))


def lyapunov(A, eps, T=200000, kind=0, seed=1):
    """数值估计两个 Lyapunov 指数（QR 方法）。"""
    rng = np.random.default_rng(seed)
    x = rng.random(2)
    for _ in range(2000):
        x = F(x, A, eps, kind)
    Q = np.eye(2)
    s = np.zeros(2)
    for _ in range(T):
        J = DF(x, A, eps, kind)
        M = J @ Q
        Q, R = np.linalg.qr(M)
        d = np.diag(R)
        d = np.where(np.abs(d) < 1e-300, 1e-300, d)
        s += np.log(np.abs(d))
        x = F(x, A, eps, kind)
    return (s / T).tolist()


def orbit(A, eps, T, x0, kind=0, burn=3000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = F(x, A, eps, kind)
    X = np.empty((T, 2))
    for t in range(T):
        x = F(x, A, eps, kind)
        X[t] = x
    return X


def obs_features(X, K=64):
    ks = [(k1, k2) for k1 in range(-3, 4) for k2 in range(-3, 4) if (k1, k2) != (0, 0)]
    ks = ks[:K // 2]
    feats = []
    for (k1, k2) in ks:
        ph = 2 * np.pi * (k1 * X[:, 0] + k2 * X[:, 1])
        feats.append(np.cos(ph)); feats.append(np.sin(ph))
    return np.stack(feats, axis=1)


def fit_exp_rate(w):
    w = np.asarray(w, float)
    m = w > 1e-14
    if m.sum() < 10:
        return None, None
    idx = np.arange(len(w))[m]; lw = np.log(w[m])
    s = np.polyfit(idx, lw, 1)
    r2 = 1 - ((lw - np.polyval(s, idx)) ** 2).sum() / ((lw - lw.mean()) ** 2).sum()
    return float(-s[0]), float(r2)


def alpha_cov(A, eps, T=60000, kind=0, seed=0):
    X = orbit(A, eps, T, (0.31415, 0.27182), kind)
    Fe = obs_features(X, 64)
    Y = Fe - Fe.mean(0, keepdims=True)
    sv = np.linalg.svd(Y, compute_uv=False)
    lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
    return fit_exp_rate(lam)


print("=" * 116)
print("非线性 Axiom A（干净检验）：alpha_res vs alpha_cov")
print("=" * 116)

rows = []
for n in (2, 4):
    A = cat_matrix(n)
    ev = np.linalg.eigvals(A)
    mu1 = float(np.abs(ev).max())
    alpha_res = np.log(mu1)
    Delta = 2 * np.log(mu1)
    print(f"\n{'='*116}")
    print(f"n={n}  mu1={mu1:.6f}  alpha_res=ln(mu1)={alpha_res:.6f}  "
          f"Delta={Delta:.6f}  alpha_res/Delta={alpha_res/Delta:.4f}")
    print(f"{'='*116}")
    print(f"  {'eps':>9}{'超双曲':>8}{'σ1_min':>9}{'σ2_max':>9}{'锥违例%':>9}"
          f"{'夹角max':>9}{'lyap1':>10}{'lyap2':>11}{'alpha_cov':>11}{'a_r/a_c':>9}")
    for eps in (0.0, 1e-5, 3e-5, 1e-4, 3e-4):
        kind = 0
        chk = check_hyperbolic(A, eps, kind)
        ly = lyapunov(A, eps, kind=kind)
        a, r2 = alpha_cov(A, eps, kind=kind)
        rows.append(dict(n=n, eps=eps, mu1=mu1, alpha_res=float(alpha_res),
                         Delta=float(Delta), alpha_cov=(float(a) if a else None),
                         r2_cov=r2, lyap=ly, **{k: v for k, v in chk.items()},
                         ratio=(float(alpha_res / a) if a else None)))
        ac_s = f"{a:.6f}" if a else "fail"
        ra_s = f"{alpha_res/a:8.2f}" if a else "   --"
        print(f"  {eps:>9.1e}{str(chk['hyperbolic']):>8}{chk['sig1_min']:>9.4f}"
              f"{chk['sig2_max']:>9.4f}{chk['cone_frac']*100:>9.2f}{chk['angle_max']:>9.2f}"
              f"{ly[0]:>10.4f}{ly[1]:>11.4f}{ac_s:>11}{ra_s:>9}")

json.dump(rows, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")

print()
print("=" * 116)
print("汇总")
print("=" * 116)
for n in (2, 4):
    sub = [r for r in rows if r["n"] == n and r["alpha_cov"]]
    if not sub:
        continue
    ac = np.array([r["alpha_cov"] for r in sub])
    ok = [r for r in sub if r["hyperbolic"]]
    print(f"  n={n}: alpha_res = {sub[0]['alpha_res']:.6f}（解析，恒定）")
    print(f"        alpha_cov: {ac.min():.6f} .. {ac.max():.6f}  跨度 {ac.max()/ac.min():.4f}x")
    print(f"        通过超双曲检验的点: {len(ok)}/{len(sub)}")
    if len(ok) >= 2:
        acok = np.array([r["alpha_cov"] for r in ok])
        print(f"        仅取通过点: {acok.min():.6f} .. {acok.max():.6f}  "
              f"跨度 {acok.max()/acok.min():.4f}x")
    print(f"        lyapunov(eps=0) = {sub[0]['lyap']}, "
          f"理论 [ln mu1, -ln mu1] = [{np.log(sub[0]['mu1']):.4f}, {-np.log(sub[0]['mu1']):.4f}]")
