# -*- coding: utf-8 -*-
"""V24 阶段六：用 horizon-τ（与饱和无关）度量在多系统上复核假设。

问题：h=50/100 时误差饱和于 ~1.0（混沌系统的可预测性极限），度量再次退化。
修正：性能 = **horizon-τ**，即归一化误差首次超过阈值 0.3 的步数（越大越好）。
      该量不饱和，能分辨性能。

系统：Lorenz63, Rossler, L96_N10（三个不同维数/复杂度）
"""
import io, os, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12"


def rk4(fn, x, dt):
    k1 = fn(x); k2 = fn(x + .5*dt*k1); k3 = fn(x + .5*dt*k2); k4 = fn(x + dt*k3)
    return x + dt/6*(k1 + 2*k2 + 2*k3 + k4)


def traj(fn, x0, dt, ns, every, burn=8000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = rk4(fn, x, dt)
    X = np.empty((ns, len(x0)))
    for i in range(ns):
        for _ in range(every):
            x = rk4(fn, x, dt)
        X[i] = x
    return X


f63 = lambda x: np.array([10*(x[1]-x[0]), x[0]*(28-x[2])-x[1], x[0]*x[1]-8/3*x[2]])
fro = lambda x: np.array([-x[1]-x[2], x[0]+0.2*x[1], 0.2+x[2]*(x[0]-5.7)])
f96 = lambda x: (np.roll(x, -1) - np.roll(x, 2)) * np.roll(x, 1) - x + 8.0

SYS = {}
SYS["Lorenz63"] = traj(f63, [1, 1, 1], 0.002, 30000, 25)
SYS["Rossler"] = traj(fro, [1, 1, 1], 0.005, 30000, 20)
SYS["L96_N10"] = traj(f96, 8 + 0.01*np.random.default_rng(1).standard_normal(10),
                      0.005, 30000, 6)


def poly_dict(Zm, deg):
    n = Zm.shape[1]
    cols = []
    idx = [tuple(t) for t in _compositions(n, deg)]
    for ex in idx:
        if sum(ex) == 0:
            continue
        c = np.ones(len(Zm))
        for j, e in enumerate(ex):
            if e:
                c = c * (Zm[:, j] ** e)
        cols.append(c)
    return np.column_stack(cols)


def _compositions(n, deg):
    if n == 1:
        for d in range(deg + 1):
            yield (d,)
        return
    for d in range(deg + 1):
        for rest in _compositions(n - 1, deg - d):
            yield (d,) + rest


def delay_dict(Zm, m, s):
    T = len(Zm) - (m - 1) * s
    return np.column_stack([Zm[i * s:i * s + T] for i in range(m)])


def rbf_dict(Zm, nc, gamma, seed=0):
    rng = np.random.default_rng(seed)
    C = Zm[rng.choice(len(Zm), nc, replace=False)]
    D2 = ((Zm[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    Phi = np.exp(-gamma * D2)
    sd = Phi.std(0); sd[sd < 1e-12] = 1.0
    return (Phi - Phi.mean(0)) / sd


def fit_ridge(An, Ap, lams=(1e-10, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0)):
    ntr = int(0.7 * len(An))
    A, B = An[:ntr], Ap[:ntr]
    G = A.T @ A
    nv = int(0.15 * len(An))
    best, bl = None, None
    for lam in lams:
        K = np.linalg.solve(G + lam*np.eye(G.shape[0]), A.T @ B)
        ve = np.linalg.norm(An[ntr:ntr+nv] @ K - Ap[ntr:ntr+nv], "fro")
        if best is None or ve < best:
            best, bl = ve, lam
    return np.linalg.solve(G + bl*np.eye(G.shape[0]), A.T @ B), ntr, bl


def analyze(A, tol=1e-3):
    Ac = A - A.mean(0, keepdims=True)
    Ap, An = Ac[1:], Ac[:-1]
    K, ntr, bl = fit_ridge(An, Ap)
    resid = Ap[:ntr] - An[:ntr] @ K
    delta = float(np.linalg.norm(resid, "fro") / max(np.linalg.norm(Ap[:ntr], "fro"), 1e-300))
    G = An[:ntr].T @ An[:ntr] / ntr
    sv = np.linalg.svd(G, compute_uv=False)
    r_tol = int((sv / sv[0] > tol).sum())
    r_eff = float(sv.sum()**2 / (sv**2).sum())
    rho = float(np.max(np.abs(np.linalg.eigvals(K))))
    return dict(Kdim=A.shape[1], r_tol=r_tol, r_eff=r_eff, delta=delta, rho=rho, lam=bl), K, ntr


def horizon_tau(K, A, ntr, thr=0.3, n_ic=60, hmax=200):
    """归一化误差首次超过 thr 的步数（越大越好）。"""
    Ac = A - A.mean(0, keepdims=True)
    Ap, An = Ac[1:], Ac[:-1]
    te = slice(ntr, len(An) - hmax)
    A0 = An[te][:n_ic]
    if len(A0) == 0:
        return np.nan
    At = Ap[te][:n_ic]
    base = np.linalg.norm(At, "fro")
    P = A0.copy()
    for h in range(1, hmax + 1):
        P = P @ K
        if not np.all(np.isfinite(P)):
            return h
        if np.linalg.norm(P - At, "fro") / max(base, 1e-300) > thr:
            return h
    return hmax


CFG = {
 "poly d=1": lambda Z_: poly_dict(Z_, 1),
 "poly d=2": lambda Z_: poly_dict(Z_, 2),
 "poly d=3": lambda Z_: poly_dict(Z_, 3),
 "delay m=2": lambda Z_: delay_dict(Z_, 2, 1),
 "delay m=3": lambda Z_: delay_dict(Z_, 3, 1),
 "delay m=5": lambda Z_: delay_dict(Z_, 5, 1),
 "delay m=8": lambda Z_: delay_dict(Z_, 8, 1),
 "rbf nc=8 g=0.5": lambda Z_: rbf_dict(Z_, 8, 0.5),
 "rbf nc=16 g=0.5": lambda Z_: rbf_dict(Z_, 16, 0.5),
 "rbf nc=32 g=0.5": lambda Z_: rbf_dict(Z_, 32, 0.5),
 "rbf nc=16 g=0.1": lambda Z_: rbf_dict(Z_, 16, 0.1),
 "rbf nc=32 g=0.1": lambda Z_: rbf_dict(Z_, 32, 0.1),
}

ALL = {}
for sn, Xr in SYS.items():
    Zs = (Xr - Xr.mean(0)) / Xr.std(0)
    print("=" * 118)
    print(f"系统 {sn}  形状 {Zs.shape}")
    print("=" * 118)
    print(f"  {'字典':<16}{'r_tol':>6}{'r_eff':>7}{'δ':>10}{'ρ(K)':>9}{'horizon-τ':>11}")
    print("-" * 118)
    R = {}
    for lab, fn in CFG.items():
        A = fn(Zs)
        if A.shape[1] > 400 or A.shape[1] < 3:
            continue
        m, K, ntr = analyze(A)
        tau = horizon_tau(K, A, ntr)
        R[lab] = dict(**m, tau=tau)
        print(f"  {lab:<16}{m['r_tol']:>6}{m['r_eff']:>7.3f}{m['delta']:>10.5f}"
              f"{m['rho']:>9.4f}{tau:>11}")
    print("-" * 118)
    labs = list(R)
    if len(labs) >= 5:
        dl = np.array([R[l]["delta"] for l in labs])
        rt = np.array([R[l]["r_tol"] for l in labs], float)
        rE = np.array([R[l]["r_eff"] for l in labs])
        rh = np.array([R[l]["rho"] for l in labs])
        tv = np.array([R[l]["tau"] for l in labs], float)
        print(f"  corr(δ,τ)={np.corrcoef(dl,tv)[0,1]:+.3f}  "
              f"corr(r_tol,τ)={np.corrcoef(rt,tv)[0,1]:+.3f}  "
              f"corr(r_eff,τ)={np.corrcoef(rE,tv)[0,1]:+.3f}  "
              f"corr(ρ,τ)={np.corrcoef(rh,tv)[0,1]:+.3f}")
        # 固定秩对照
        items = list(R.items())
        print("  固定秩对照（δ 变化 vs τ 变化）：")
        shown = 0
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (l1, m1), (l2, m2) = items[i], items[j]
                if abs(m1["r_tol"] - m2["r_tol"]) <= 1 and m1["tau"] and m2["tau"]:
                    dr = m2["delta"] / max(m1["delta"], 1e-12)
                    dt_ = m2["tau"] / max(m1["tau"], 1e-12)
                    if abs(np.log(max(dr, 1e-12))) > 1.0 and shown < 4:
                        print(f"    {l1:<16}(r={m1['r_tol']},δ={m1['delta']:.4f},τ={m1['tau']})")
                        print(f"    {l2:<16}(r={m2['r_tol']},δ={m2['delta']:.4f},τ={m2['tau']})")
                        print(f"      δ 比 {dr:.3f}×  ->  τ 比 {dt_:.3f}×\n")
                        shown += 1
    print()
    ALL[sn] = R
json.dump(ALL, io.open(os.path.join(OUT, "v24_multisys.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("saved v24_multisys.json")
