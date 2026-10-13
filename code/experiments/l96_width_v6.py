# -*- coding: utf-8 -*-
"""CORRECTED real-system width scan on the Lorenz-96 flow map (N=40, F=8).

The v3/v5 scan used a plain DeepONet and never learned (test MSE ~6.6 in raw units,
6.6x WORSE than the trivial predictor). Here the architecture is fixed
(Fourier-feature trunk + per-field bias), every width is reported against three
reference curves, and the width law gamma is fitted only where the model is
actually learning (below the trivial baseline).

Baselines (normalised test MSE): trivial 1.0001, persistence 0.2453, ridge 0.1630.
"""
import os, json, time
import numpy as np
import torch

ROOT = r"E:\nature投稿\探索1\数值验证"
OUT = os.path.join(ROOT, "real_l96_width_v6.json")
d = np.load(os.path.join(ROOT, "_real_l96_data.npz"), allow_pickle=True)
Xtr = torch.tensor(d["Xtrn"].astype(np.float32)); Ytr = torch.tensor(d["Ytrn"].astype(np.float32))
Xte = torch.tensor(d["Xten"].astype(np.float32)); Yte = torch.tensor(d["Yten"].astype(np.float32))
N = int(d["N"])
xc = torch.tensor((np.arange(N) / float(N - 1)).reshape(-1, 1).astype(np.float32))
b = np.load(os.path.join(ROOT, "_l96_baselines.npy"))
mse_zero, mse_pers, mse_lin = [float(v) for v in b]
torch.set_num_threads(max(1, os.cpu_count() or 1))
print(f"N={N} | trivial {mse_zero:.4f} | persistence {mse_pers:.4f} | ridge {mse_lin:.4f}", flush=True)


class MLPModel(torch.nn.Module):
    def __init__(self, bw, w, nf=8, sigma=3.0):
        super().__init__()
        self.register_buffer("B", torch.randn(1, nf) * sigma)
        self.net = torch.nn.Sequential(
            torch.nn.Linear(bw + 2 * nf, w), torch.nn.Tanh(),
            torch.nn.Linear(w, w), torch.nn.Tanh(),
            torch.nn.Linear(w, w), torch.nn.Tanh(),
            torch.nn.Linear(w, 1))
        self.bias = torch.nn.Parameter(torch.zeros(bw))

    def forward(self, a, x):
        z = x @ self.B
        ff = torch.cat([torch.sin(z), torch.cos(z)], dim=-1).unsqueeze(0).expand(a.shape[0], -1, -1)
        inp = torch.cat([a.unsqueeze(1).expand(-1, x.shape[0], -1), ff], dim=-1)
        return self.net(inp).squeeze(-1) + self.bias


def train(width, seed, epochs, lr=1e-3, bs=512):
    torch.manual_seed(seed)
    net = MLPModel(N, width)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=800, min_lr=1e-5)
    n = Xtr.shape[0]
    for ep in range(epochs):
        ii = torch.randperm(n)[:bs]
        loss = torch.mean((net(Xtr[ii], xc) - Ytr[ii]) ** 2)
        opt.zero_grad(); loss.backward(); opt.step(); sch.step(loss.detach())
    with torch.no_grad():
        mse = float(torch.mean((net(Xte, xc) - Yte) ** 2))
    return mse


W_LIST = [16, 24, 32, 48, 64, 96, 128, 256]
SEEDS = [0, 1, 2]
EPOCHS = 6000
sweep = {}
t_start = time.time()
for W in W_LIST:
    vals = []
    for sd in SEEDS:
        t0 = time.time()
        m = train(W, sd, EPOCHS)
        vals.append(m)
        print(f"  W={W:4d} seed={sd}  MSE={m:.4f}  ({time.time()-t0:.0f}s)", flush=True)
    sweep[str(W)] = dict(mse_mean=float(np.mean(vals)), mse_std=float(np.std(vals, ddof=1)),
                         per_seed=vals)
    print(f"  W={W:4d} -> mean {sweep[str(W)]['mse_mean']:.4f} +/- {sweep[str(W)]['mse_std']:.4f}",
          flush=True)

Ws = np.array([float(w) for w in sweep])
Ms = np.array([sweep[str(int(w))]["mse_mean"] for w in Ws])
rmse = np.sqrt(Ms)
rmse_triv = np.sqrt(mse_zero)

# fit gamma only where the model beats both trivial and persistence
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

# W*(eps) by interpolation on the measured curve
Wstar = {}
for eps in (0.40, 0.30, 0.25, 0.20, 0.15, 0.12, 0.10):
    target = eps                                  # normalised RMSE already
    cross = np.where((rmse[:-1] >= target) & (rmse[1:] <= target))[0]
    if len(cross) == 0:
        Wstar[str(eps)] = None if rmse[-1] > target else int(Ws[-1])
    else:
        i = cross[0]
        lw, lr_ = np.log(Ws[i]), np.log(rmse[i])
        hw, hr = np.log(Ws[i + 1]), np.log(rmse[i + 1])
        frac = (np.log(target) - lr_) / (hr - lr_)
        Wstar[str(eps)] = int(round(np.exp(lw + frac * (hw - lw))))

out = dict(system="Lorenz-96 (N=40, F=8) flow map u(t)->u(t+tau)",
           tau_steps=int(d["N"]) if False else 10,
           architecture="MLP on (state, 8 random Fourier features of coordinate), 3 hidden layers, output bias",
           epochs=int(EPOCHS), seeds=SEEDS, widths=[int(w) for w in Ws],
           sweep=sweep,
           baselines=dict(trivial=mse_zero, persistence=mse_pers, ridge_linear=mse_lin),
           rmse_mean=[float(r) for r in rmse],
           rmse_trivial=float(rmse_triv),
           beats_trivial=bool(np.all(Ms < mse_zero)),
           beats_persistence_at=[int(w) for w in Ws[Ms < mse_pers]],
           beats_ridge_at=[int(w) for w in Ws[Ms < mse_lin]],
           gamma=gamma, gamma_R2=gamma_r2,
           gamma_fit_widths=[int(w) for w in Ws[mask]],
           W_star=Wstar,
           elapsed_s=time.time() - t_start)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\n" + json.dumps({k: out[k] for k in ("gamma", "gamma_R2", "W_star", "beats_trivial",
                                             "beats_persistence_at", "beats_ridge_at")}, indent=2))
print(f"\nsaved {OUT}  ({out['elapsed_s']:.0f}s)")
