# -*- coding: utf-8 -*-
"""V17-任务1（修正版）：严格盲测，18 个系统。

判据与阈值**事前公布**（见文件头部常量，写定后不再修改）。
KS 使用与稿件一致的现有数据（path2_ks_turb.npz）。
"""
import json, os
import numpy as np
from scipy.linalg import svd as csvd

OUT = r"E:\deepseekworkspace\experiments_v12"
NUM = r"E:\nature投稿\探索1\数值验证"
os.makedirs(OUT, exist_ok=True)

TH = dict(alpha_n_min=2.0, r2_min=0.90, rho_max=0.5, r2_rho=0.97,
          fit_lo=0.10, fit_hi=0.90, beta_min=0.5)
print("事前公布阈值:", json.dumps(TH, ensure_ascii=False))


def classify(lam, th=TH):
    lam = np.sort(np.asarray(lam, float))[::-1]
    lam = lam[lam > 1e-13 * lam[0]]
    n = len(lam); k = np.arange(1, n + 1)
    o = dict(n=n, rho=float(lam[-1] / lam[0]))
    lo = max(2, int(np.ceil(th["fit_lo"] * n))); hi = max(6, int(np.floor(th["fit_hi"] * n)))
    m = (k >= lo) & (k <= hi)
    if m.sum() < 6:
        o.update(cls="饱和", rule="R0", reason="拟合点不足"); return o
    y = np.log(lam[m])
    cE = np.polyfit(k[m], y, 1)
    r2E = 1 - ((y - np.polyval(cE, k[m]))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    cP = np.polyfit(np.log(k[m]), y, 1)
    r2P = 1 - ((y - np.polyval(cP, np.log(k[m])))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    a, b = float(-cE[0]), float(-cP[0])
    o.update(r2E=float(r2E), r2P=float(r2P), alpha=a, beta=b, alpha_n=float(a * n))
    if o["alpha_n"] < th["alpha_n_min"]:
        o.update(cls="饱和", rule="R1", reason=f"αn={o['alpha_n']:.2f}")
    elif max(r2E, r2P) < th["r2_min"]:
        o.update(cls="饱和", rule="R2", reason=f"maxR²={max(r2E,r2P):.3f}")
    elif o["rho"] > th["rho_max"] and max(r2E, r2P) < th["r2_rho"]:
        o.update(cls="饱和", rule="R3", reason=f"ρ={o['rho']:.2f}")
    elif r2E >= r2P:
        o.update(cls="对数", rule="R4", pred=(1 / a if a > 0 else None))
    else:
        if b > th["beta_min"]:
            o.update(cls="幂律", rule="R5", pred=1 / (b - 0.5))
        else:
            o.update(cls="饱和", rule="R5b", reason=f"β={b:.3f}")
    return o


EPS = np.logspace(-1, -8, 90)


def r_curve(lam, eps=EPS):
    lam = np.sort(np.asarray(lam, float))[::-1]
    e2 = lam ** 2
    tail = np.cumsum(e2[::-1])[::-1]
    rel = np.sqrt(np.maximum(tail / e2.sum(), 0))
    return np.minimum(np.array([min(int(np.searchsorted(-rel, -e)) + 1, len(lam))
                                for e in eps], float), len(lam))


def measured(lam, eps=EPS):
    r = r_curve(lam, eps)
    if r.max() / max(r.min(), 1) < 1.5:
        return dict(cls="饱和", note=f"r 变化 {r.max()/max(r.min(),1):.2f}×")
    m = (r > 0) & (r < r.max())
    if m.sum() < 6:
        return dict(cls="饱和", note="未饱和点不足")
    y, x = r[m], np.log(1 / eps[m])
    sl, ic = np.polyfit(x, y, 1)
    r2l = 1 - ((y - (sl * x + ic))**2).sum() / max(((y - y.mean())**2).sum(), 1e-300)
    xp, yp = np.log(eps[m]), np.log(r[m])
    p, c = np.polyfit(xp, yp, 1)
    r2p = 1 - ((yp - (p * xp + c))**2).sum() / max(((yp - yp.mean())**2).sum(), 1e-300)
    return dict(cls=("对数" if r2l > r2p else "幂律"), log_slope=float(sl), log_R2=float(r2l),
                pow_exp=float(-p), pow_R2=float(r2p), r_min=int(r[m].min()), r_max=int(r[m].max()))


def rk4(fn, x, dt):
    k1 = fn(x); k2 = fn(x + .5*dt*k1); k3 = fn(x + .5*dt*k2); k4 = fn(x + dt*k3)
    return x + dt/6*(k1 + 2*k2 + 2*k3 + k4)


def traj(fn, x0, dt, ns, every, burn=5000):
    x = np.array(x0, float)
    for _ in range(burn):
        x = rk4(fn, x, dt)
    X = np.empty((ns, len(x0)))
    for i in range(ns):
        for _ in range(every):
            x = rk4(fn, x, dt)
        X[i] = x
    return X


def emb(ts, m, stride, cap=120000):
    T = len(ts) - (m - 1) * stride
    return np.stack([ts[i*stride:i*stride+T] for i in range(m)], 1)[:cap]


rng = np.random.default_rng(2024)
SYS = {}
SYS["Lorenz63"] = traj(lambda x: np.array([10*(x[1]-x[0]), x[0]*(28-x[2])-x[1], x[0]*x[1]-8/3*x[2]]), [1,1,1], 0.002, 60000, 25)
SYS["Rossler"] = traj(lambda x: np.array([-x[1]-x[2], x[0]+0.2*x[1], 0.2+x[2]*(x[0]-5.7)]), [1,1,1], 0.005, 80000, 20)
SYS["Chen"] = traj(lambda x: np.array([35*(x[1]-x[0]), -7*x[0]+28*x[1]-x[0]*x[2], x[0]*x[1]-3*x[2]]), [1,1,1], 0.002, 60000, 25)
SYS["Lorenz84"] = traj(lambda x: np.array([-1.8*x[0]+x[1]*x[2], -1.2*x[1]+x[0]*x[2], -0.6*x[2]+x[0]*x[1]]), [1,1,1], 0.005, 60000, 20)
for N in (6, 10, 20, 40):
    f = lambda x: (np.roll(x,-1)-np.roll(x,2))*np.roll(x,1)-x+8.0
    SYS[f"L96_N{N}"] = traj(f, 8+0.01*rng.standard_normal(N), 0.005, 80000, 6)


def mackey_glass(npts, beta=0.2, gamma=0.1, tau=17.0, n=10.0, dt=0.05, x0=1.2):
    hl = int(tau/dt)+2; hist = np.full(hl, x0); ptr = hl-1; lag = int(tau/dt)
    out = np.empty(npts)
    for i in range(npts):
        u = hist[ptr]; ud = hist[(ptr-lag) % hl]
        f = lambda a, b: beta*b/(1.0+b**n)-gamma*a
        k1=f(u,ud); k2=f(u+.5*dt*k1,ud); k3=f(u+.5*dt*k2,ud); k4=f(u+dt*k3,ud)
        xn=u+dt/6*(k1+2*k2+2*k3+k4); ptr=(ptr+1)%hl; hist[ptr]=xn; out[i]=xn
    return out
MG = mackey_glass(1_600_000)[50_000:]
SYS["MG_m12"] = emb(MG[::12], 12, 3)
SYS["MG_m20"] = emb(MG[::12], 20, 3)


def logistic(n, r=3.99, x0=0.4):
    x = np.empty(n); x[0] = x0
    for i in range(1, n):
        x[i] = r*x[i-1]*(1-x[i-1])
    return x
def henon(n, a=1.4, b=0.3):
    X = np.empty((n,2)); X[0]=[0.1,0.1]
    for i in range(1,n):
        X[i,0]=1-a*X[i-1,0]**2+X[i-1,1]; X[i,1]=b*X[i-1,0]
    return X
def ikeda(n, u=0.918):
    X=np.empty((n,2)); x=y=0.1
    for i in range(n):
        t=0.4-6/(1+x*x+y*y)
        x,y = 1+u*(x*np.cos(t)-y*np.sin(t)), u*(x*np.sin(t)+y*np.cos(t))
        X[i]=[x,y]
    return X
SYS["Logistic_m16"] = emb(logistic(600000)[1000:], 16, 2)
SYS["Henon_m12"] = emb(henon(400000)[1000:,0], 12, 2)
SYS["Ikeda"] = ikeda(400000)[1000:]


def cml(L, ec, a, n, burn=5000):
    st = 0.4+0.2*np.random.default_rng(3).random(L)
    f = lambda z: a*z*(1-z)
    for _ in range(burn):
        st = (1-ec)*f(st)+ec*0.5*(np.roll(f(st),1)+np.roll(f(st),-1))
    S = np.empty((n,L))
    for i in range(n):
        st = (1-ec)*f(st)+ec*0.5*(np.roll(f(st),1)+np.roll(f(st),-1)); S[i]=st
    return S[500:]
SYS["CML_L64"] = cml(64, 0.20, 3.9, 120000)
SYS["CML_L128"] = cml(128, 0.10, 3.9, 120000)
SYS["CML_L256"] = cml(256, 0.05, 3.9, 100000)

# KS：用稿件同源数据（L=22, N=32）
ks = np.load(os.path.join(NUM, "path2_ks_turb.npz"))["ksf"]
SYS["KS_L22_N32"] = ks[:120000]
# 与 v17 新算的 L=64 KS
p2 = os.path.join(OUT, "ks_v17_traj.npy")
if os.path.exists(p2):
    SYS["KS_L11_N64"] = np.load(p2)

print(f"\n系统数: {len(SYS)}")
print("=" * 118)
print("盲测（判据事前公布；预测仅用协方差谱）")
print("=" * 118)
print(f"  {'系统':<14}{'n':>6}{'ρ':>9}{'R²_E':>8}{'R²_P':>8}{'αn':>7}  预测     规则  实测    一致")
print("-" * 118)
RES = {}; hit = tot = 0; fails = []
for nm, X in SYS.items():
    lam = csvd(X - X.mean(0, keepdims=True), compute_uv=False) ** 2
    c = classify(lam); mc = measured(lam)
    ok = c["cls"] == mc["cls"]; hit += ok; tot += 1
    if not ok:
        fails.append((nm, c, mc))
    RES[nm] = dict(n=int(c["n"]), predict=c, measured=mc, agree=bool(ok))
    print(f"  {nm:<14}{c['n']:>6}{c['rho']:>9.4f}{c.get('r2E',float('nan')):>8.4f}"
          f"{c.get('r2P',float('nan')):>8.4f}{c.get('alpha_n',float('nan')):>7.2f}"
          f"  {c['cls']:<7}{c['rule']:<5}{mc['cls']:<7}{'✓' if ok else '✗'}")
print("-" * 118)
print(f"  盲测一致率: {hit}/{tot} = {hit/tot*100:.1f}%")
if fails:
    print("\n  失败案例:")
    for nm, c, mc in fails:
        print(f"    {nm}: 预测 {c['cls']}(规则{c['rule']}: {c.get('reason','')})"
              f"  实测 {mc['cls']}({mc.get('note','')})")
json.dump(dict(thresholds=TH, results=RES, hit=hit, tot=tot, fails=[f[0] for f in fails]),
          open(os.path.join(OUT, "v17_blind_test.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nsaved v17_blind_test.json")
