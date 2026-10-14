# -*- coding: utf-8 -*-
"""路 B 步骤 2：分支翻转扩到 ≥3 个真实系统（含 tapering 稳健性检验）。

反查要点（避免上轮的方法缺陷）
==============================
上轮用**未加窗**的自协方差 R(L)，长滞后估计噪声可能污染 Toeplitz。
本轮**同时**用：
  (i)  未加窗 R(L)                —— 复现上轮
  (ii) Tukey 加窗 R(L)·w(L)       —— 稳健版
若两者给出**同样的翻转模式**，则翻转不是估计噪声造成。
"""
import io, json, os
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v28_branch_multi.json"
PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"


def fits(lam, skip=2):
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    lam = np.maximum(lam, 1e-300)
    k = np.arange(1, len(lam) + 1)
    m = (k >= skip) & (lam > lam.max() * 1e-12)
    if m.sum() < 6:
        return np.nan, np.nan
    lv = np.log(lam[m])
    s1 = np.polyfit(k[m], lv, 1)
    r2e = 1 - ((lv - np.polyval(s1, k[m])) ** 2).sum() / ((lv - lv.mean()) ** 2).sum()
    s2 = np.polyfit(np.log(k[m]), lv, 1)
    r2p = 1 - ((lv - np.polyval(s2, np.log(k[m]))) ** 2).sum() / ((lv - lv.mean()) ** 2).sum()
    return float(r2e), float(r2p)


def toeplitz_lam(R, n):
    idx = np.arange(n)
    return np.sort(np.linalg.eigvalsh(R[np.abs(idx[:, None] - idx[None, :])]))[::-1]


def autocorr(ts, M):
    """ts: (T, d) 主成分时间序列。"""
    T = len(ts)
    ts = ts - ts.mean(0, keepdims=True)
    R = np.empty(M + 1)
    for L in range(M + 1):
        R[L] = np.mean(np.sum(ts[:T - L] * ts[L:], axis=1))
    return R / max(R[0], 1e-300)


def taper(R, kind="tukey"):
    M = len(R) - 1
    L = np.arange(M + 1)
    if kind == "none":
        return R
    w = 0.5 * (1 + np.cos(np.pi * L / M))
    return R * w


# ---- 取真实轨迹 ----
def get_ts(fn, kind, n_pc=8, n_traj=1):
    """返回若干条 (T, n_pc) 的主要时间序列。"""
    out = []
    if kind == "pde":
        import h5py
        p = os.path.join(PD, fn)
        if not os.path.exists(p):
            return None
        with h5py.File(p, "r") as f:
            keys = [k for k in f.keys()
                    if isinstance(f[k], h5py.Dataset) and f[k].ndim >= 2]
            ten = f["tensor"] if "tensor" in f else f[keys[0]]
            ntr = ten.shape[0]
            idx = np.linspace(0, ntr - 1, min(n_traj, ntr)).astype(int)
            for i in idx:
                field = np.asarray(ten[int(i)], dtype=np.float64)
                if field.ndim > 2:
                    field = field.reshape(field.shape[0], -1)
                Y = np.nan_to_num(field - field.mean(0, keepdims=True))
                U, S, _ = np.linalg.svd(Y, full_matrices=False)
                out.append((U[:, :n_pc] * S[:n_pc]))
    else:
        rows = []
        p = os.path.join(FD, fn)
        if not os.path.exists(p):
            return None
        for line in io.open(p, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rows.append([float(x) for x in line.split()])
            except ValueError:
                continue
        return None  # 静态谱无时间序列
    return out


print("=" * 116)
print("路 B 步骤 2：分支翻转（多系统 + tapering 稳健性）")
print("=" * 116)

CASES = [("Advection beta=1.0", "1D_Advection_Sols_beta1.0.hdf5", "pde"),
         ("Advection beta=4.0", "1D_Advection_Sols_beta4.0.hdf5", "pde"),
         ("Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "pde")]
NS = (16, 32, 64, 128, 160)
results = []
for nm, fn, kind in CASES:
    series = get_ts(fn, kind, n_pc=8, n_traj=3)
    if not series:
        print(f"\n  [缺] {nm}")
        continue
    print(f"\n{'='*116}")
    print(f"### {nm}   ({len(series)} 条轨迹)")
    print(f"{'='*116}")
    for window in ("none", "tukey"):
        print(f"  --- R 加窗: {window} ---")
        print(f"  {'轨迹':>5}" + "".join(f"{'n='+str(n):>11}" for n in NS))
        seqs = []
        for si, ts in enumerate(series):
            R = autocorr(ts, max(NS))
            Rt = taper(R, window)
            line = f"  {si:>5}"
            ws = []
            for n in NS:
                if n >= len(Rt):
                    line += f"{'--':>11}"
                    continue
                lam = toeplitz_lam(Rt, n)
                r2e, r2p = fits(lam)
                w = "E" if r2e > r2p else "A"
                ws.append(w)
                line += f"{w+format(max(r2e,r2p),'.3f'):>11}"
            seqs.append("".join(ws))
            print(line)
        for si, sq in enumerate(seqs):
            fl = len(set(sq)) > 1
            results.append(dict(system=nm, window=window, traj=si,
                                seq=sq, flipped=fl))
        nfl = sum(1 for sq in seqs if len(set(sq)) > 1)
        print(f"        翻转轨迹: {nfl}/{len(seqs)}")

print()
print("=" * 116)
print("汇总")
print("=" * 116)
print(f"  {'系统':>24}{'加窗':>9}{'翻转轨迹数':>12}{'总轨迹':>8}")
for nm, fn, kind in CASES:
    for window in ("none", "tukey"):
        sub = [r for r in results if r["system"] == nm and r["window"] == window]
        if sub:
            nfl = sum(1 for s in sub if s["flipped"])
            print(f"  {nm:>24}{window:>9}{nfl:>12}{len(sub):>8}")
print()
print("""  判读：若**未加窗**与**Tukey 加窗**给出**相同的翻转结论**，
  则翻转不是长滞后估计噪声造成的假象，而是 Toeplitz 谱的真实结构。""")

json.dump(results, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n已保存 {OUT}")
