# -*- coding: utf-8 -*-
"""V17-任务3：饱和类的标度 —— 有效维数 d_eff 与系统尺度/物理参数的关系。

动机：饱和类的秩由 n（有效维数）限制。若能把 n 与可直接测的物理量
      （系统尺度 L、耦合强度、Re、Lyapunov 维数 D_KY）连起来，
      该类的模型规模就**可事前估计**。

检验三件事：
  T3.1  d_eff 与状态维 n 的关系（CML 族 L=32..256；L96 族 N=6..40）
  T3.2  d_eff 与 Kaplan–Yorke 维数 D_KY 的关系（L96 族，可精确算 D_KY）
  T3.3  按 Cleary–Page (2024) 的 d_A ~ Re^{1/3} 思路，检验 d_eff 对
        控制参数（L96 的 F、CML 的耦合强度）的标度
"""
import json, os
import numpy as np
from scipy.linalg import svd as csvd, qr

OUT = r"E:\deepseekworkspace\experiments_v12"
os.makedirs(OUT, exist_ok=True)


def rk4(fn, x, dt):
    k1 = fn(x); k2 = fn(x + .5*dt*k1); k3 = fn(x + .5*dt*k2); k4 = fn(x + dt*k3)
    return x + dt/6*(k1 + 2*k2 + 2*k3 + k4)


def traj(fn, x0, dt, ns, every, burn=20000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = rk4(fn, x, dt)
    X = np.empty((ns, len(x0)))
    for i in range(ns):
        for _ in range(every):
            x = rk4(fn, x, dt)
        X[i] = x
    return X


def d_eff_of(X):
    sv = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
    return float(sv.sum()**2 / (sv**2).sum()), sv


# ---------- Lyapunov / D_KY（变分方程 + Benettin QR） ----------
def J_l96(x, F=8.0):
    n = len(x); J = np.zeros((n, n))
    for i in range(n):
        J[i, i] = -1.0
        J[i, (i-1) % n] += x[(i+1) % n] - x[(i-2) % n]
        J[i, (i+1) % n] += x[(i-1) % n]
        J[i, (i-2) % n] -= x[(i-1) % n]
    return J


def lyap_l96(N, F=8.0, dt=0.005, nsteps=40000, burn=20000):
    f = lambda x: (np.roll(x,-1)-np.roll(x,2))*np.roll(x,1)-x+F
    x = F + 0.01*np.random.default_rng(1).standard_normal(N)
    for _ in range(burn):
        x = rk4(f, x, dt)
    Q = np.eye(N); acc = np.zeros(N)
    for _ in range(nsteps):
        k1=f(x);K1=J_l96(x,F)@Q
        x2=x+.5*dt*k1;k2=f(x2);K2=J_l96(x2,F)@(Q+.5*dt*K1)
        x3=x+.5*dt*k2;k3=f(x3);K3=J_l96(x3,F)@(Q+.5*dt*K2)
        x4=x+dt*k3;k4=f(x4);K4=J_l96(x4,F)@(Q+dt*K3)
        x=x+dt/6*(k1+2*k2+2*k3+k4)
        Q,R=qr(Q+dt/6*(K1+2*K2+2*K3+K4)); acc+=np.log(np.abs(np.diag(R)))
    return np.sort(acc/(nsteps*dt))[::-1]


def d_ky(lam):
    lam = np.asarray(lam, float); S = np.cumsum(lam)
    k = int(np.sum(S > 0))
    if k == 0:
        return 0.0
    if k >= len(lam):
        return float(k)
    return float(k + S[k-1]/abs(lam[k]))


print("=" * 104)
print("T3.1  d_eff 与状态维 n")
print("=" * 104)
print(f"  {'系统':<14}{'n':>6}{'d_eff':>9}{'d_eff/n':>9}")
R1 = {}
for N in (6, 10, 20, 40, 80):
    f = lambda x: (np.roll(x,-1)-np.roll(x,2))*np.roll(x,1)-x+8.0
    X = traj(f, 8+0.01*np.random.default_rng(1).standard_normal(N), 0.005, 60000, 6)
    de, _ = d_eff_of(X)
    R1[f"L96_N{N}"] = dict(n=N, d_eff=de, ratio=de/N)
    print(f"  {'L96_N'+str(N):<14}{N:>6}{de:>9.3f}{de/N:>9.3f}")


def cml(L, ec, a, n, burn=8000):
    st = 0.4+0.2*np.random.default_rng(3).random(L)
    f = lambda z: a*z*(1-z)
    for _ in range(burn):
        st = (1-ec)*f(st)+ec*0.5*(np.roll(f(st),1)+np.roll(f(st),-1))
    S = np.empty((n,L))
    for i in range(n):
        st = (1-ec)*f(st)+ec*0.5*(np.roll(f(st),1)+np.roll(f(st),-1)); S[i]=st
    return S[500:]
for L, ec in ((32,0.30),(64,0.20),(128,0.10),(256,0.05)):
    X = cml(L, ec, 3.9, 60000)
    de, _ = d_eff_of(X)
    R1[f"CML_L{L}"] = dict(n=L, eps=ec, d_eff=de, ratio=de/L)
    print(f"  {'CML_L'+str(L):<14}{L:>6}{de:>9.3f}{de/L:>9.3f}")

print("\n" + "=" * 104)
print("T3.2  d_eff 与 Kaplan–Yorke 维数 D_KY（L96 族）")
print("=" * 104)
print(f"  {'系统':<10}{'N':>5}{'D_KY':>9}{'d_eff':>9}{'d_eff/D_KY':>12}{'d_eff/N':>9}")
R2 = {}
for N in (6, 10, 20, 40, 80):
    lam_ly = lyap_l96(N)
    D = d_ky(lam_ly)
    de = R1[f"L96_N{N}"]["d_eff"]
    R2[f"N{N}"] = dict(N=N, D_KY=D, d_eff=de, r1=de/D, r2=de/N, lyap=[float(v) for v in lam_ly[:5]])
    print(f"  {'L96_N'+str(N):<10}{N:>5}{D:>9.2f}{de:>9.3f}{de/D:>12.3f}{de/N:>9.3f}")

print("\n" + "=" * 104)
print("T3.3  饱和类 n 对控制参数的标度（L96 的 F）")
print("=" * 104)
print(f"  {'F':>6}{'N=40 的 d_eff':>15}{'D_KY':>9}{'d_eff/D_KY':>12}")
R3 = {}
for F in (5.0, 6.0, 7.0, 8.0, 9.0):
    fn = lambda x, F=F: (np.roll(x,-1)-np.roll(x,2))*np.roll(x,1)-x+F
    X = traj(fn, F+0.01*np.random.default_rng(1).standard_normal(40), 0.005, 60000, 6)
    de, _ = d_eff_of(X)
    lam_ly = lyap_l96(40, F=F, nsteps=30000)
    D = d_ky(lam_ly)
    R3[f"F{F}"] = dict(F=F, d_eff=de, D_KY=D, ratio=de/D)
    print(f"  {F:>6.1f}{de:>15.3f}{D:>9.2f}{de/D:>12.3f}")

print("\n" + "=" * 104)
print("标度检验")
print("=" * 104)
# CML: d_eff vs L 的幂指数
Ls = np.array([32, 64, 128, 256], float)
des = np.array([R1[f"CML_L{int(L)}"]["d_eff"] for L in Ls])
m = des > 0
if m.sum() >= 3:
    p = np.polyfit(np.log(Ls[m]), np.log(des[m]), 1)
    r2 = 1-((np.log(des[m])-np.polyval(p, np.log(Ls[m])))**2).sum()/ \
            ((np.log(des[m])-np.log(des[m]).mean())**2).sum()
    print(f"  CML: d_eff ~ L^{p[0]:.3f}  (R²={r2:.3f})")
# L96: d_eff vs N
Ns = np.array([6, 10, 20, 40, 80], float)
deN = np.array([R1[f"L96_N{int(N)}"]["d_eff"] for N in Ns])
p2 = np.polyfit(np.log(Ns), np.log(deN), 1)
r22 = 1-((np.log(deN)-np.polyval(p2, np.log(Ns)))**2).sum()/ \
        ((np.log(deN)-np.log(deN).mean())**2).sum()
print(f"  L96: d_eff ~ N^{p2[0]:.3f}     (R²={r22:.3f})")
# d_eff vs D_KY
DK = np.array([R2[f"N{int(N)}"]["D_KY"] for N in Ns])
p3 = np.polyfit(np.log(DK), np.log(deN), 1)
r23 = 1-((np.log(deN)-np.polyval(p3, np.log(DK)))**2).sum()/ \
        ((np.log(deN)-np.log(deN).mean())**2).sum()
print(f"  L96: d_eff ~ D_KY^{p3[0]:.3f}  (R²={r23:.3f})")
print(f"\n  比值 d_eff/D_KY 范围: {min(v['r1'] for v in R2.values()):.3f} – "
      f"{max(v['r1'] for v in R2.values()):.3f}")
json.dump(dict(T31=R1, T32=R2, T33=R3,
               scaling_cml=dict(exp=float(p[0]), r2=float(r2)) if m.sum() >= 3 else None,
               scaling_l96_N=dict(exp=float(p2[0]), r2=float(r22)),
               scaling_l96_DKY=dict(exp=float(p3[0]), r2=float(r23))),
          open(os.path.join(OUT, "v17_saturation_scaling.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nsaved v17_saturation_scaling.json")
