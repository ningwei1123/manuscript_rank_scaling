# -*- coding: utf-8 -*-
"""
Real-system neural-operator width-law experiment (addresses reviewer M3/M5).

Emulates the flow map of the REAL Lorenz-96 system (N=40, F=8), a chaotic ODE
whose singular-value spectrum is algebraic with beta ~ 0.025 (independently
estimated below from the snapshot POD spectrum).

For each width W we train a DeepONet (branch: state u(t) at N sensor points;
trunk: coordinate index) to predict u(t+tau), averaged over several seeds to
give error bars. We fit the width law E(W) ~ W^{-gamma} and compare the
measured gamma to the operator-theory prediction 2*beta (for a map whose
singular spectrum decays as k^{-beta}, rank ~ epsilon^{-1/beta} and, with
W* proportional to r*, E(W) ~ W^{-2*beta}).

Output: real_l96_width_t01.json
"""
import os, json, time
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
TORCH_PY = "C:/Users/Administrator/.venv-torch/Scripts/python.exe"

def l96_rhs(x, F):
    N = len(x)
    dx = np.empty(N)
    for i in range(N):
        dx[i] = (x[(i+1) % N] - x[i-2]) * x[i-1] - x[i] + F
    return dx

def rk4_step(f, x, dt):
    k1=f(x); k2=f(x+0.5*dt*k1); k3=f(x+0.5*dt*k2); k4=f(x+dt*k3)
    return x + dt/6.0*(k1+2*k2+2*k3+k4)

def trajectory(N, F, T, dt, seed=0, transient=20.0):
    rng = np.random.default_rng(seed)
    x = 0.5*rng.standard_normal(N)
    for _ in range(int(transient/dt)):
        x = rk4_step(lambda xx: l96_rhs(xx, F), x, dt)
    n = int(T/dt)
    out = np.empty((n+1, N)); out[0] = x
    for i in range(n):
        x = rk4_step(lambda xx: l96_rhs(xx, F), x, dt); out[i+1] = x
    return out

def lyap_and_dky(N, F, T=200.0, dt=0.01, ng=0.5, seed=0):
    from scipy.linalg import qr as qr_s
    rng = np.random.default_rng(seed)
    x = 0.5*rng.standard_normal(N); Q = np.eye(N); sums = np.zeros(N)
    nsteps = int(round(T/dt)); ngi = max(1, int(round(ng/dt))); tacc = 0.0
    for i in range(nsteps):
        x = rk4_step(lambda xx: l96_rhs(xx, F), x, dt)
        Jv = lambda Qm: np.stack([_jac_vec(x, Qm[:, j], F, N) for j in range(Q.shape[1])], axis=1)
        Q = rk4_step(Jv, Q, dt)
        if (i+1) % ngi == 0:
            Q, R = qr_s(Q); sums += np.log(np.abs(np.diag(R))); tacc += ngi*dt
    lyap = np.sort(sums/tacc)[::-1]
    s = np.cumsum(lyap); k = int(np.searchsorted(-s, 0.0))
    dky = k + s[k-1]/np.abs(lyap[k]) if k > 0 else 0.0
    return lyap, dky

def _jac_vec(x, v, F, N):
    Jv = np.empty(N)
    for i in range(N):
        a = x[(i+1) % N] - x[i-2]
        Jv[i] = a*v[i-1] + x[i-1]*v[(i+1) % N] - x[i-1]*v[i-2] - v[i]
    return Jv

def estimate_beta(states):
    """Algebraic tail fit log sigma_k ~ -beta log k. Returns fits at several
    tail thresholds plus the upper-half fit, since the asymptotic exponent is
    fit-sensitive and must be trace-class (beta > 0.5)."""
    from scipy.linalg import svd
    sv = svd(states - states.mean(0), full_matrices=False, compute_uv=False)
    sv = sv/sv[0]; k = np.arange(1, len(sv)+1)
    fits = {}
    for thr in (0.2, 0.1, 0.05):
        tail = k[sv < thr]
        if len(tail) >= 5:
            kt = tail.astype(float); ys = np.log(sv[tail-1])
            A = np.vstack([np.log(kt), np.ones_like(kt)]).T
            coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
            pred = A @ coef
            r2 = 1 - np.sum((ys-pred)**2)/np.sum((ys-ys.mean())**2)
            fits[f"thr{int(thr*100):03d}"] = (float(-coef[0]), float(r2), int(tail[0]))
    # upper-half (most asymptotic) fit
    h = len(k)//2
    kt = k[h:].astype(float); ys = np.log(sv[h:])
    A = np.vstack([np.log(kt), np.ones_like(kt)]).T
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    pred = A @ coef
    r2 = 1 - np.sum((ys-pred)**2)/np.sum((ys-ys.mean())**2)
    fits["upperhalf"] = (float(-coef[0]), float(r2), int(k[h]))
    # pick the fit with smallest threshold that still has good R2 (most asymptotic)
    best = min((f for f in fits.values() if f[1] > 0.95),
               key=lambda f: f[2], default=None)
    beta = best[0] if best else fits["upperhalf"][0]
    return float(beta), float(fits["upperhalf"][1]), int(fits["upperhalf"][2]), fits, [float(v) for v in sv[:15].tolist()]

def main():
    import subprocess
    t0 = time.time()
    N, F, dt = 40, 8.0, 0.01
    traj = trajectory(N, F, T=4000.0, dt=dt, seed=12345)
    tau_steps = 10  # tau = 0.1 (shorter, learnable horizon)
    X = traj[:-tau_steps]; Y = traj[tau_steps:]
    idx = np.arange(0, len(X), 4); X, Y = X[idx], Y[idx]
    n = len(X); n_tr = int(0.8*n)
    Xtr, Ytr = X[:n_tr], Y[:n_tr]; Xte, Yte = X[n_tr:], Y[n_tr:]
    bmean = Xtr.mean(0); bstd = Xtr.std(0)+1e-6
    ymean = Ytr.mean(0); ystd = Ytr.std(0)+1e-6
    Xtrn=(Xtr-bmean)/bstd; Xten=(Xte-bmean)/bstd
    Ytrn=(Ytr-ymean)/ystd; Yten=(Yte-ymean)/ystd
    xcoord = (np.arange(N)/float(N-1)).reshape(-1,1).astype(np.float32)

    lyap, dky = lyap_and_dky(N, F, seed=777)
    beta, beta_r2, k0, fits, s_top = estimate_beta(Xtr)
    print("   beta fits:", {kk: (round(v[0],3), round(v[1],3), v[2]) for kk, v in fits.items()})
    print(f"[real-L96] D_KY={dky:.3f} beta={beta:.4f} (R2={beta_r2:.3f}, tail k>={k0}) n_train={n_tr}", flush=True)

    # data file for the torch subprocess
    data_path = os.path.join(ROOT, "_real_l96_data.npz")
    np.savez(data_path, Xtrn=Xtrn, Ytrn=Ytrn, Xten=Xten, Yten=Yten, xcoord=xcoord,
             bmean=bmean, bstd=bstd, ymean=ymean, ystd=ystd, N=np.array(N))
    W_list = [8,16,24,32,48,64]; seeds = [0,1,2,3]; epochs = 1500

    train_script = f'''import os, json, numpy as np, torch
d = np.load(r"{data_path}", allow_pickle=True)
N=int(d["N"]); Xtrn=d["Xtrn"].astype(np.float32); Ytrn=d["Ytrn"].astype(np.float32)
Xten=d["Xten"].astype(np.float32); Yten=d["Yten"].astype(np.float32)
xcoord=d["xcoord"].astype(np.float32); ymean=d["ymean"].astype(np.float32); ystd=d["ystd"].astype(np.float32)
W_list={W_list}; seeds={seeds}; epochs={epochs}
class DeepONet(torch.nn.Module):
    def __init__(self,bw,tw,w,L=3):
        super().__init__()
        b=[torch.nn.Linear(bw,w),torch.nn.Tanh()]
        for _ in range(L-1): b+=[torch.nn.Linear(w,w),torch.nn.Tanh()]
        self.branch=torch.nn.Sequential(*b)
        t=[torch.nn.Linear(tw,w),torch.nn.Tanh()]
        for _ in range(L-1): t+=[torch.nn.Linear(w,w),torch.nn.Tanh()]
        self.trunk=torch.nn.Sequential(*t); self.out=torch.nn.Linear(w,1,bias=False)
    def forward(self,a,x): return torch.sum(self.branch(a)[:,None,:]*self.trunk(x)[None,:,:],dim=-1)
thtr=torch.tensor(Xtrn); ytr=torch.tensor(Ytrn); thte=torch.tensor(Xten); yte=torch.tensor(Yten)
xc=torch.tensor(xcoord); ystd_t=torch.tensor(ystd); nt=thtr.shape[0]; res={{}}
for W in W_list:
    res[str(W)]={{}}
    for sd in seeds:
        torch.manual_seed(sd); net=DeepONet(N,1,W,3); opt=torch.optim.Adam(net.parameters(),lr=1e-3)
        sch=torch.optim.lr_scheduler.ReduceLROnPlateau(opt,factor=0.5,patience=400,min_lr=1e-5)
        for ep in range(epochs):
            ii=torch.randperm(nt)[:256]; pred=net(thtr[ii],xc); loss=torch.mean((pred-ytr[ii])**2)
            opt.zero_grad(); loss.backward(); opt.step(); sch.step(loss.detach())
        with torch.no_grad():
            pred=net(thte,xc)*ystd_t+torch.tensor(ymean); mse=torch.mean((pred-yte)**2).item()
        res[str(W)][str(sd)]=float(mse); print(f"   W={{W}} sd={{sd}} testMSE={{mse:.3e}}",flush=True)
json.dump(res,open(r"{os.path.join(ROOT,'real_l96_sweep_t01.json')}","w"),indent=2); print("DONE",flush=True)
'''
    tpath = os.path.join(ROOT, "_real_l96_train.py")
    with open(tpath, "w") as f:
        f.write(train_script)
    subprocess.run([TORCH_PY, tpath], check=True)

    sweep = json.load(open(os.path.join(ROOT, "real_l96_sweep_t01.json")))
    Ws = np.array(W_list)
    mean_mse=[]; std_mse=[]
    for W in Ws:
        vals = np.array([sweep[str(int(W))][str(sd)] for sd in seeds])
        mean_mse.append(vals.mean()); std_mse.append(vals.std())
    mean_mse=np.array(mean_mse); std_mse=np.array(std_mse)
    ystd_all = float(Ytr.std()); rmse=np.sqrt(mean_mse)
    m = rmse > 1e-3*ystd_all
    if m.sum() >= 3:
        A = np.vstack([np.log(Ws[m]), np.ones(m.sum())]).T
        coef, *_ = np.linalg.lstsq(A, np.log(rmse[m]), rcond=None)
        pred = A @ coef; ss=((np.log(rmse[m])-pred)**2).sum(); tot=((np.log(rmse[m])-np.log(rmse[m]).mean())**2).sum()
        gamma=float(-coef[0]); gamma_r2=float(1-ss/tot)
    else:
        gamma, gamma_r2 = float("nan"), float("nan")
    Wstar={}
    for e in [0.30,0.25,0.20]:
        target=e*ystd_all; cross=np.where((rmse[:-1]>=target)&(rmse[1:]<=target))[0]
        if len(cross)==0: Wstar[str(e)]=None if rmse[-1]>target else int(Ws[-1])
        else:
            i=cross[0]; lw,lr=np.log(Ws[i]),np.log(rmse[i]); hw,hr=np.log(Ws[i+1]),np.log(rmse[i+1])
            frac=(np.log(target)-lr)/(hr-lr); Wstar[str(e)]=int(round(np.exp(lw+frac*(hw-lw))))
    out = {"system":"Lorenz-96 (N=40,F=8) flow map u(t)->u(t+0.5)",
           "D_KY":float(dky),"beta":beta,"beta_R2":beta_r2,"beta_tail_k0":k0,"sigma_top15":s_top,
           "gamma_measured":gamma,"gamma_R2":gamma_r2,"gamma_predicted_2beta":2*beta,
           "W_list":[int(w) for w in Ws],"mse_mean":[float(v) for v in mean_mse],
           "mse_std":[float(v) for v in std_mse],"rmse_mean_rel":[float(v/ystd_all) for v in rmse],
           "W_star_relrmse":Wstar,"elapsed_s":time.time()-t0}
    json.dump(out, open(os.path.join(ROOT,"real_l96_width_t01.json"),"w"), indent=2)
    print("REAL-L96 RESULT:", json.dumps({k:out[k] for k in ["D_KY","beta","beta_R2","gamma_measured","gamma_R2","gamma_predicted_2beta","W_star_relrmse"]}, indent=2))
    print("done in %.1fs" % (time.time()-t0))

if __name__ == "__main__":
    main()
