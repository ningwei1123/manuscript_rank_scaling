# -*- coding: utf-8 -*-
"""精度对照：float32 vs float64 在**完全相同**配置下的宽度指数。

这是本轮的核心问题：float32 是否因机器精度地板污染了 gamma？
float32 的 eps ≈ 1.19e-7，MSE 地板 ≈ 1.4e-14（绝对值）。
若真实 MSE 降到 1e-6 以下，float32 仍有余量；但若降到 1e-10 量级就会撞地板。
"""
import io, json, time
import numpy as np
import torch
import torch.nn as nn
from concurrent.futures import ProcessPoolExecutor, as_completed

OUT = r"E:\deepseekworkspace\experiments_v12\v13_precision_compare.json"

NTR, NTE, BATCH = 800, 400, 128
WIDTHS = [8, 16, 32, 64]
BUDGETS = [2000, 6000, 16000]
BETAS = [1.0, 0.75]
SEED = 0
D, P = 20, 16
LR = 2e-3


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


def task(args):
    beta, W, dtname = args
    torch.set_num_threads(1)
    dt = torch.float64 if dtname == "float64" else torch.float32
    op, sig = make_op(beta)
    r = np.random.default_rng(SEED)
    a_tr = r.standard_normal((NTR, D)); y_tr = a_tr @ op.T
    a_te = np.random.default_rng(SEED + 999).standard_normal((NTE, D)); y_te = a_te @ op.T
    A = torch.tensor(a_tr, dtype=dt); Y = torch.tensor(y_tr, dtype=dt)
    Ate = torch.tensor(a_te, dtype=dt); Yte = torch.tensor(y_te, dtype=dt)
    x = torch.linspace(0.0, 1.0, P, dtype=dt).reshape(-1, 1)
    torch.manual_seed(SEED)
    net = DeepONet(D, W, P).to(dt)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=800, min_lr=1e-10)
    rec = {}
    for ep in range(1, max(BUDGETS) + 1):
        perm = torch.randperm(NTR)
        for i in range(0, NTR, BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            loss = ((net(A[idx], x) - Y[idx]) ** 2).mean()
            loss.backward(); opt.step()
        sch.step(loss.detach())
        if ep in BUDGETS:
            with torch.no_grad():
                rec[ep] = float(((net(Ate, x) - Yte) ** 2).mean())
    # 训练集 MSE（判断是否过拟合）
    with torch.no_grad():
        rec["train"] = float(((net(A, x) - Y) ** 2).mean())
    return beta, W, dtname, rec


def fit_gamma(ws, rs):
    w = np.asarray(ws, float); r = np.asarray(rs, float)
    m = np.isfinite(r) & (r > 0)
    if m.sum() < 3:
        return float("nan"), float("nan")
    lw, lr = np.log(w[m]), np.log(r[m])
    s = np.polyfit(lw, lr, 1)
    r2 = 1 - ((lr - np.polyval(s, lw)) ** 2).sum() / ((lr - lr.mean()) ** 2).sum()
    return float(-s[0]), float(r2)


def main():
    print("=" * 104)
    print("精度对照：float32 vs float64（相同网络、相同数据、相同种子）")
    print("=" * 104)
    print(f"  NTR={NTR} BATCH={BATCH} widths={WIDTHS} budgets={BUDGETS} seed={SEED}")
    tasks = [(b, W, dt) for dt in ("float32", "float64")
             for b in BETAS for W in WIDTHS]
    t0 = time.time()
    store = {}
    with ProcessPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(task, t): t for t in tasks}
        for f in as_completed(futs):
            beta, W, dtname, rec = f.result()
            store.setdefault(dtname, {}).setdefault(beta, {})[W] = rec

    res = {}
    for dtname in ("float32", "float64"):
        print(f"\n{'='*104}\n{dtname}\n{'='*104}")
        for beta in BETAS:
            print(f"  --- beta={beta} ---")
            print(f"  {'budget':>8}" + "".join(f"{'W='+str(W):>13}" for W in WIDTHS)
                  + f"{'gamma':>10}{'R2':>8}")
            for b in BUDGETS:
                ws = [W for W in WIDTHS if b in store[dtname][beta][W]]
                rs = [store[dtname][beta][W][b] for W in ws]
                g, r2 = fit_gamma(ws, rs)
                res.setdefault(dtname, {}).setdefault(str(beta), {})[str(b)] = dict(
                    widths=ws, rmse=rs, gamma=g, r2=r2)
                print(f"  {b:>8}" + "".join(f"{v:>13.3e}" for v in rs) + f"{g:>10.4f}{r2:>8.4f}")
            tr = [store[dtname][beta][W].get("train") for W in WIDTHS]
            print(f"  {'train':>8}" + "".join(
                f"{(v if v is not None else float('nan')):>13.3e}" for v in tr))

    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n耗时 {(time.time()-t0)/60:.1f} 分钟；已保存 {OUT}")

    print()
    print("=" * 104)
    print("对照结论")
    print("=" * 104)
    print(f"  {'beta':>7}{'budget':>9}{'gamma f32':>12}{'gamma f64':>12}{'差异':>10}")
    for beta in BETAS:
        for b in BUDGETS:
            g32 = res["float32"][str(beta)][str(b)]["gamma"]
            g64 = res["float64"][str(beta)][str(b)]["gamma"]
            print(f"  {beta:>7}{b:>9}{g32:>12.4f}{g64:>12.4f}{abs(g32-g64):>10.4f}")


if __name__ == "__main__":
    main()
