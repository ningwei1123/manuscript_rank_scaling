# -*- coding: utf-8 -*-
"""V24 阶段七：加入条件数控制，排除「数值条件」这一混淆。

观察：多系统中 corr(δ,τ) 为负（-0.22 ~ -0.49），而高 δ 组恰是条件数差的 RBF。
需检验：是否**条件数**（而非 δ 或秩）在主导性能？
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
SYS = {"Lorenz63": traj(f63, [1, 1, 1], 0.002, 25000, 25),
       "Rossler": traj(fro, [1, 1, 1], 0.005, 25000, 20)}


def delay_dict(Zm, m, s=1):
    T = len(Zm) - (m - 1) * s
    return np.column_stack([Zm[i*s:i*s+T] for i in range(m)])


def rbf_dict(Zm, nc, gamma, seed=0):
    rng = np.random.default_rng(seed)
    C = Zm[rng.choice(len(Zm), nc, replace=False)]
    D2 = ((Zm[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    Phi = np.exp(-gamma * D2)
    sd = Phi.std(0); sd[sd < 1e-12] = 1.0
    return (Phi - Phi.mean(0)) / sd


def fit_ridge(An, Ap, lams=(1e-10, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0)):
    ntr = int(0.7 * len(An)); A, B = An[:ntr], Ap[:ntr]
    G = A.T @ A; nv = int(0.15 * len(An))
    best = bl = None
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
    condG = float(sv[0] / max(sv[-1], 1e-300))
    condA = float(np.linalg.cond(An[:ntr]))
    return dict(Kdim=A.shape[1], r_tol=r_tol, r_eff=r_eff, delta=delta, rho=rho,
                lam=bl, condG=condG, condA=condA), K, ntr


def horizon_tau(K, A, ntr, thr=0.3, n_ic=60, hmax=200):
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


CFG = {}
for m in (2, 3, 5, 8, 12):
    CFG[f"delay m={m}"] = (lambda Z_, m=m: delay_dict(Z_, m))
for nc in (8, 16, 32):
    for g in (0.05, 0.1, 0.2, 0.5, 1.0):
        CFG[f"rbf nc={nc} g={g}"] = (lambda Z_, nc=nc, g=g: rbf_dict(Z_, nc, g))

ALL = {}
for sn, Xr in SYS.items():
    Zs = (Xr - Xr.mean(0)) / Xr.std(0)
    print("=" * 120)
    print(f"系统 {sn}")
    print("=" * 120)
    print(f"  {'字典':<18}{'r_tol':>6}{'δ':>10}{'cond(A)':>11}{'ρ(K)':>9}{'τ':>5}")
    print("-" * 120)
    R = {}
    for lab, fn in CFG.items():
        A = fn(Zs)
        m, K, ntr = analyze(A)
        m["tau"] = horizon_tau(K, A, ntr)
        R[lab] = m
        print(f"  {lab:<18}{m['r_tol']:>6}{m['delta']:>10.5f}{m['condA']:>11.2e}"
              f"{m['rho']:>9.4f}{m['tau']:>5}")
    print("-" * 120)
    labs = list(R)
    dl = np.array([R[l]["delta"] for l in labs])
    rt = np.array([R[l]["r_tol"] for l in labs], float)
    rE = np.array([R[l]["r_eff"] for l in labs])
    cd = np.array([np.log10(R[l]["condA"]) for l in labs])
    rh = np.array([R[l]["rho"] for l in labs])
    tv = np.array([R[l]["tau"] for l in labs], float)
    print(f"  corr(δ,τ)={np.corrcoef(dl,tv)[0,1]:+.3f}   corr(r_tol,τ)={np.corrcoef(rt,tv)[0,1]:+.3f}"
          f"   corr(r_eff,τ)={np.corrcoef(rE,tv)[0,1]:+.3f}")
    print(f"  corr(log cond,τ)={np.corrcoef(cd,tv)[0,1]:+.3f}   corr(ρ,τ)={np.corrcoef(rh,tv)[0,1]:+.3f}")
    ALL[sn] = R
    print()
json.dump(ALL, io.open(os.path.join(OUT, "v24_condition.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("saved v24_condition.json")
