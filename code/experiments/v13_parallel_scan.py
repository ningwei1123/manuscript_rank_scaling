# -*- coding: utf-8 -*-
"""float64 + 多进程并行的受控算子宽度扫描。

关键改进（相对之前的 float32 单进程版本）：
  1. dtype = float64：float32 的 MSE 地板约 1.4e-14，而我们要测到 1e-6 以下，
     地板会污染 γ 拟合。
  2. multiprocessing：每个 (beta, W, seed, budget) 是一个独立任务，
     **天然可并行**；用 ProcessPoolExecutor 分配到多核。
  3. 每个任务内部 torch 单线程，避免线程竞争。

用法：
    python v13_parallel_scan.py --workers 8 --mode tiny
"""
import argparse, io, json, os, time
import numpy as np
import torch
import torch.nn as nn
from concurrent.futures import ProcessPoolExecutor, as_completed

OUTDIR = r"E:\deepseekworkspace\experiments_v12"

NTR, NTE, BATCH = 400, 200, 64
D, P = 20, 16


def make_op(beta, seed=0):
    r = np.random.default_rng(seed)
    U, _ = np.linalg.qr(r.standard_normal((P, D)))
    Vt, _ = np.linalg.qr(r.standard_normal((D, D)))
    k = np.arange(1, min(P, D) + 1)
    sig = np.concatenate([(k + 1.0) ** (-beta), np.zeros(max(0, P - D))])[:P]
    S = np.zeros((P, D))
    S[np.arange(len(sig)), np.arange(len(sig))] = sig
    return U @ S @ Vt, sig


class DeepONet(nn.Module):
    def __init__(self, bi, w, m, L=3):
        super().__init__()
        b = [nn.Linear(bi, w), nn.Tanh()]
        for _ in range(L - 1):
            b += [nn.Linear(w, w), nn.Tanh()]
        self.branch = nn.Sequential(*b)
        t = [nn.Linear(1, w), nn.Tanh()]
        for _ in range(L - 1):
            t += [nn.Linear(w, w), nn.Tanh()]
        self.trunk = nn.Sequential(*t)
        self.bias = nn.Parameter(torch.zeros(m))

    def forward(self, a, x):
        return self.branch(a) @ self.trunk(x).T + self.bias


def one_task(args):
    """一个 (beta, W, seed, budgets) 任务。返回 (beta, W, seed, {budget: mse})。"""
    beta, W, seed, budgets, lr, dtype_name = args
    torch.set_num_threads(1)
    dt = torch.float64 if dtype_name == "float64" else torch.float32
    op, sig = make_op(beta)
    r = np.random.default_rng(seed)
    a_tr = r.standard_normal((NTR, D)); y_tr = a_tr @ op.T
    a_te = np.random.default_rng(seed + 999).standard_normal((NTE, D)); y_te = a_te @ op.T
    A = torch.tensor(a_tr, dtype=dt); Y = torch.tensor(y_tr, dtype=dt)
    Ate = torch.tensor(a_te, dtype=dt); Yte = torch.tensor(y_te, dtype=dt)
    x = torch.linspace(0.0, 1.0, P, dtype=dt).reshape(-1, 1)
    torch.manual_seed(seed)
    net = DeepONet(D, W, P).to(dt)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    sch = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, factor=0.5, patience=max(200, max(budgets) // 20), min_lr=1e-9)
    rec = {}
    for ep in range(1, max(budgets) + 1):
        perm = torch.randperm(NTR)
        for i in range(0, NTR, BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            loss = ((net(A[idx], x) - Y[idx]) ** 2).mean()
            loss.backward(); opt.step()
        sch.step(loss.detach())
        if ep in budgets:
            with torch.no_grad():
                rec[ep] = float(((net(Ate, x) - Yte) ** 2).mean())
    return beta, W, seed, rec


def fit_gamma(ws, rs):
    w = np.asarray(ws, dtype=float)
    r = np.asarray(rs, dtype=float)
    m = np.isfinite(r) & (r > 0)
    if m.sum() < 3:
        return float("nan"), float("nan")
    lw, lr = np.log(w[m]), np.log(r[m])
    s = np.polyfit(lw, lr, 1)
    pred = np.polyval(s, lw)
    r2 = 1 - ((lr - pred) ** 2).sum() / ((lr - lr.mean()) ** 2).sum()
    return float(-s[0]), float(r2)


MODES = {
    "tiny":  dict(widths=[6, 16, 48], budgets=[1000, 4000, 12000],
                  betas=[1.0, 0.75], seeds=[0], lr=2e-3),
    "mid":   dict(widths=[4, 6, 10, 16, 24, 48, 96], budgets=[2000, 8000, 32000],
                  betas=[1.0, 0.75], seeds=[0, 1], lr=2e-3),
    "wide":  dict(widths=[4, 6, 8, 12, 16, 24, 32, 48, 64, 96], budgets=[2000, 8000, 32000],
                  betas=[1.0, 0.75], seeds=[0, 1], lr=2e-3),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="tiny", choices=list(MODES))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4)))
    ap.add_argument("--dtype", default="float64", choices=["float32", "float64"])
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    cfg = MODES[a.mode]

    tasks = []
    for beta in cfg["betas"]:
        for W in cfg["widths"]:
            for sd in cfg["seeds"]:
                tasks.append((beta, W, sd, tuple(cfg["budgets"]), cfg["lr"], a.dtype))

    print("=" * 100)
    print(f"并行宽度扫描  mode={a.mode}  dtype={a.dtype}  workers={a.workers}")
    print(f"  任务数 {len(tasks)}   widths={cfg['widths']}  budgets={cfg['budgets']}")
    print(f"  betas={cfg['betas']}  seeds={cfg['seeds']}  cpu={os.cpu_count()}")
    print("=" * 100, flush=True)

    t0 = time.time()
    done = 0
    store = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one_task, t): t for t in tasks}
        for f in as_completed(futs):
            beta, W, sd, rec = f.result()
            store.setdefault(beta, {}).setdefault(W, {})[sd] = rec
            done += 1
            print(f"  [{done}/{len(tasks)}] beta={beta} W={W} seed={sd}  "
                  f"MSE@max={rec[max(cfg['budgets'])]:.3e}  ({time.time()-t0:.0f}s)", flush=True)

    # 汇总
    res = {}
    print()
    for beta in cfg["betas"]:
        print(f"--- beta={beta} ---")
        print(f"  {'budget':>8}" + "".join(f"{'W='+str(W):>13}" for W in cfg["widths"])
              + f"{'gamma':>10}{'R2':>8}")
        for b in cfg["budgets"]:
            ws, rs = [], []
            for W in cfg["widths"]:
                vals = [store[beta][W][sd][b] for sd in cfg["seeds"] if sd in store[beta][W]]
                if vals:
                    ws.append(W); rs.append(float(np.mean(vals)))
            g, r2 = fit_gamma(ws, rs)
            res.setdefault(str(beta), {})[str(b)] = dict(widths=ws, rmse=rs,
                                                        gamma=g, r2=r2, dtype=a.dtype)
            print(f"  {b:>8}" + "".join(f"{v:>13.3e}" for v in rs)
                  + f"{g:>10.4f}{r2:>8.4f}")

    tag = a.tag or f"{a.mode}_{a.dtype}"
    p = os.path.join(OUTDIR, f"v13_scan_{tag}.json")
    json.dump(dict(config=dict(a.__dict__), results=res), io.open(p, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"\n耗时 {(time.time()-t0)/60:.1f} 分钟；已保存 {p}")

    print()
    print("=" * 100)
    print("结论")
    print("=" * 100)
    for beta in cfg["betas"]:
        gs = [res[str(beta)][str(b)]["gamma"] for b in cfg["budgets"]]
        print(f"  beta={beta}: gamma " + " -> ".join(f"{g:.4f}" for g in gs))
        print(f"            理论: 算子范数 gamma={beta}, Frobenius gamma={beta-0.5}")


if __name__ == "__main__":
    main()
