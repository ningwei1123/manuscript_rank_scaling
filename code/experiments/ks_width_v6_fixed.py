# -*- coding: utf-8 -*-
"""KS width scan at a properly constructed horizon.

Bug fixed: the earlier slice `Xc[TAU::STRIDE]` produced a separation of only
STRIDE-independent 500 steps regardless of TAU, so the task was 4x easier than
intended. The paired arrays are now built explicitly:
    X[i] = field[i*STRIDE]        Y[i] = field[i*STRIDE + TAU_STEPS]

Runs TAU_STEPS = 2000 (0.5 model time units), where the mean-centred field has
autocorrelation 0.863 and persistence gives rel. RMSE ~0.505.
"""
import os, json, sys, time
import numpy as np
import torch

ROOT = r"E:\nature投稿\探索1\数值验证"
TAU_STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
STRIDE = 8
NTR, NTE = 8000, 2000
EPOCHS, SEEDS = 8000, [0, 1]
W_LIST = [8, 16, 24, 32, 48, 64, 96, 128]
OUT = os.path.join(ROOT, f"ks_width_v6_tau{TAU_STEPS}.json")

f = np.load(os.path.join(ROOT, "path2_ks_turb.npz"))["ksf"]
N = f.shape[1]
Xc = f - f.mean(axis=0, keepdims=True)
scale = float(Xc.std())

idx = np.arange(0, len(f) - TAU_STEPS, STRIDE)
X = Xc[idx] / scale
Y = Xc[idx + TAU_STEPS] / scale
# Guard added after a subsampling bug produced an EMPTY test set in the first attempt.
assert len(X) >= NTR + NTE, (
    f"not enough pairs for the declared split: have {len(X)}, need {NTR + NTE}; "
    f"reduce STRIDE or NTR/NTE.")
X, Y = X[:NTR + NTE], Y[:NTR + NTE]
Xtr, Ytr, Xte, Yte = X[:NTR], Y[:NTR], X[NTR:], Y[NTR:]
assert len(Xte) == NTE and len(Xtr) == NTR, "split sizes do not match the declaration"

sep_check = float(np.sqrt(np.mean((Xtr - Ytr) ** 2)))
print(f"field {f.shape} N={N}  tau={TAU_STEPS} steps = {TAU_STEPS*2.5e-4:.3f} t.u.", flush=True)
print(f"train {Xtr.shape} test {Xte.shape}  scale={scale:.4f}", flush=True)
print(f"[check] train persistence rel.RMSE = {sep_check:.4f}", flush=True)

mse_zero = float(np.mean(Yte ** 2))
mse_pers = float(np.mean((Xte - Yte) ** 2))
lam = 1e-3
Wr = np.linalg.solve(Xtr.T @ Xtr + lam * np.eye(N), Xtr.T @ Ytr)
mse_lin = float(np.mean((Xte @ Wr - Yte) ** 2))
print(f"baselines rel.MSE: trivial {mse_zero:.4f} | persistence {mse_pers:.4f} | ridge {mse_lin:.4f}",
      flush=True)
print(f"baselines rel.RMSE: trivial {np.sqrt(mse_zero):.4f} | persistence {np.sqrt(mse_pers):.4f} "
      f"| ridge {np.sqrt(mse_lin):.4f}", flush=True)

Xtr_t = torch.tensor(Xtr.astype(np.float32)); Ytr_t = torch.tensor(Ytr.astype(np.float32))
Xte_t = torch.tensor(Xte.astype(np.float32)); Yte_t = torch.tensor(Yte.astype(np.float32))
torch.set_num_threads(max(1, os.cpu_count() or 1))


class MLP(torch.nn.Module):
    def __init__(self, bw, w):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(bw, w), torch.nn.Tanh(),
            torch.nn.Linear(w, w), torch.nn.Tanh(),
            torch.nn.Linear(w, w), torch.nn.Tanh(),
            torch.nn.Linear(w, bw))

    def forward(self, a):
        return self.net(a)


def train(width, seed, lr=1e-3, bs=256):
    torch.manual_seed(seed)
    net = MLP(N, width)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=1000, min_lr=1e-6)
    n = Xtr_t.shape[0]
    for ep in range(EPOCHS):
        ii = torch.randperm(n)[:bs]
        loss = torch.mean((net(Xtr_t[ii]) - Ytr_t[ii]) ** 2)
        opt.zero_grad(); loss.backward(); opt.step(); sch.step(loss.detach())
    with torch.no_grad():
        return float(torch.mean((net(Xte_t) - Yte_t) ** 2))


sweep, t_start = {}, time.time()
for W in W_LIST:
    vals = []
    for sd in SEEDS:
        t0 = time.time()
        m = train(W, sd); vals.append(m)
        print(f"  W={W:4d} seed={sd} rel.MSE={m:.5f} rel.RMSE={np.sqrt(m):.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    sweep[str(W)] = dict(mse_mean=float(np.mean(vals)), mse_std=float(np.std(vals, ddof=1)),
                         per_seed=vals)
    print(f"  W={W:4d} -> {sweep[str(W)]['mse_mean']:.5f} +/- {sweep[str(W)]['mse_std']:.5f}",
          flush=True)

Ws = np.array([float(w) for w in sweep])
Ms = np.array([sweep[str(int(w))]["mse_mean"] for w in Ws])
rmse = np.sqrt(Ms)
mask = Ms < mse_pers
if mask.sum() >= 3:
    A = np.vstack([np.log(Ws[mask]), np.ones(mask.sum())]).T
    coef, *_ = np.linalg.lstsq(A, np.log(rmse[mask]), rcond=None)
    pred = A @ coef
    ss = ((np.log(rmse[mask]) - pred) ** 2).sum()
    tot = ((np.log(rmse[mask]) - np.log(rmse[mask]).mean()) ** 2).sum()
    gamma, gamma_r2 = float(-coef[0]), float(1 - ss / tot)
else:
    gamma, gamma_r2 = float("nan"), float("nan")

A2 = np.vstack([Ws, np.ones_like(Ws)]).T
c2, *_ = np.linalg.lstsq(A2, np.log(rmse), rcond=None)
pred2 = A2 @ c2
ss2 = ((np.log(rmse) - pred2) ** 2).sum(); tot2 = ((np.log(rmse) - np.log(rmse).mean()) ** 2).sum()
log_slope, log_r2 = float(-c2[0]), float(1 - ss2 / tot2)

Wstar = {}
for eps in (0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20):
    cross = np.where((rmse[:-1] >= eps) & (rmse[1:] <= eps))[0]
    if len(cross) == 0:
        Wstar[str(eps)] = None if rmse[-1] > eps else int(Ws[-1])
    else:
        i = cross[0]
        lw, lr_ = np.log(Ws[i]), np.log(rmse[i])
        hw, hr = np.log(Ws[i + 1]), np.log(rmse[i + 1])
        frac = (np.log(eps) - lr_) / (hr - lr_)
        Wstar[str(eps)] = int(round(np.exp(lw + frac * (hw - lw))))

out = dict(system="Kuramoto-Sivashinsky L=22 N=32 (path2_ks_turb.npz, RK4 field)",
           tau_steps=TAU_STEPS, dt=2.5e-4, tau=TAU_STEPS * 2.5e-4, stride=STRIDE,
           pair_construction="X[i]=field[i*STRIDE], Y[i]=field[i*STRIDE+TAU_STEPS]",
           normalisation="relative to global std of the mean-centred field",
           n_train=NTR, n_test=NTE, epochs=EPOCHS, seeds=SEEDS,
           architecture="MLP 32->W->W->W->32, tanh",
           widths=[int(w) for w in Ws], sweep=sweep,
           baselines=dict(trivial=mse_zero, persistence=mse_pers, ridge_linear=mse_lin),
           rmse_mean=[float(r) for r in rmse],
           beats_persistence=bool(np.any(Ms < mse_pers)),
           beats_ridge=bool(np.any(Ms < mse_lin)),
           gamma_powerlaw=gamma, gamma_powerlaw_R2=gamma_r2,
           gamma_fit_widths=[int(w) for w in Ws[mask]],
           loglaw_slope=log_slope, loglaw_R2=log_r2,
           W_star=Wstar, elapsed_s=time.time() - t_start)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print("\n" + json.dumps({k: out[k] for k in ("tau", "gamma_powerlaw", "gamma_powerlaw_R2",
                                             "loglaw_slope", "loglaw_R2", "W_star",
                                             "beats_persistence", "beats_ridge")}, indent=2))
print(f"\nsaved {OUT} ({out['elapsed_s']:.0f}s)")
