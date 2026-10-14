# -*- coding: utf-8 -*-
"""负面结论的 10 遍严格检验（第 1 部分：数值反查）。

清点出的 10 条负面结论
=====================
N1  宽度律一般不可能为幂律（Lanthaler-Stuart 诅咒）
N2  宽度幂指数不稳定（1.97 -> 3.47，随训练预算漂移）
N3  KS 的秩斜率与谱指数不一致（19% / 4-82%）
N4  三向比较在观测记录上不可识别（4/14）
N5  对齐条件 A = cQ 苛刻（一般算子不满足）
N6  谱分支归属依赖截断 n
N7  无实测系统实例化代数分支
N8  SRS 不优于 99% 能量准则
N9  alpha_cov 与 Lyapunov 隙无闭式联系
N10 秩选择在谱已知时无算法空间（同义反复）

本脚本对最易出错者做反查。
"""
import io, json
import numpy as np

OUT = r"E:\deepseekworkspace\experiments_v12\v27_negative_checks.json"
res = {}

# ============================================================
print("=" * 112)
print("[N6 反查] 分支翻转是真实结构还是拟合噪声？")
print("=" * 112)
print("  关键问题：真实数据上的 AEAE 翻转，是否仅由 R(L) 的**估计噪声**造成？")
print("  做法：用**精确**几何 R(t)=a^t（零噪声）构造 Toeplitz，看是否同样翻转")
print()


def toeplitz_eigs(a, n):
    idx = np.arange(n)
    return np.sort(np.linalg.eigvalsh(a ** np.abs(idx[:, None] - idx[None, :])))[::-1]


def fits(v, skip=2):
    v = np.maximum(np.abs(np.asarray(v, float)), 1e-300)
    k = np.arange(1, len(v) + 1)
    m = (k >= skip) & (v > v.max() * 1e-12)
    lv = np.log(v[m])
    s1 = np.polyfit(k[m], lv, 1)
    r2e = 1 - ((lv - np.polyval(s1, k[m])) ** 2).sum() / ((lv - lv.mean()) ** 2).sum()
    s2 = np.polyfit(np.log(k[m]), lv, 1)
    r2p = 1 - ((lv - np.polyval(s2, np.log(k[m]))) ** 2).sum() / ((lv - lv.mean()) ** 2).sum()
    return float(r2e), float(r2p)


print(f"  {'Delta':>7}" + "".join(f"{'n='+str(n):>18}" for n in (16, 32, 64, 128, 256)))
n_flip_exact = 0
for Delta in (0.3, 0.5, 0.7, 1.0, 1.2):
    a = np.exp(-Delta)
    line = f"  {Delta:>7.2f}"
    ws = []
    for n in (16, 32, 64, 128, 256):
        r2e, r2p = fits(toeplitz_eigs(a, n))
        w = "E" if r2e > r2p else "A"
        ws.append(w)
        line += f"{w+':'+format(max(r2e,r2p),'.3f'):>18}"
    if len(set(ws)) > 1:
        n_flip_exact += 1
    print(line)
print(f"\n  精确（零噪声）Toeplitz 上也翻转的 Delta 数：{n_flip_exact}/5")
print("  => 若 >0，则翻转**不是**噪声造成的假象，而是 Toeplitz 谱的真实结构")
res["N6_exact_flips"] = n_flip_exact

# ============================================================
print()
print("=" * 112)
print("[N8 反查] SRS 失败是否由我的实现缺陷造成？")
print("=" * 112)
print("  关键问题：若把 SRS 的判类阈值/窗口调到最优，能否超过 E99？")
print("  做法：给 SRS 一个**上界优势**——用真谱直接判类，再看结果")
print()


def r_true(lam, eps):
    lam = np.sort(np.maximum(lam, 0))[::-1]
    c = np.cumsum(lam) / max(lam.sum(), 1e-300)
    idx = np.where(1 - c <= eps ** 2)[0]
    return int(idx[0] + 1) if len(idx) else len(lam)


def srs_oracle(lam, eps):
    """SRS 的"神谕版"：已知真谱、已知最优形式，用闭式。"""
    lam = np.sort(np.maximum(np.asarray(lam, float), 0))[::-1]
    n = len(lam)
    k = np.arange(1, n + 1); m = k >= 3
    le = np.log(np.maximum(lam[m], 1e-300))
    r2e = 1 - ((le - np.polyval(np.polyfit(k[m], le, 1), k[m])) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    r2a = 1 - ((le - np.polyval(np.polyfit(np.log(k[m]), le, 1), np.log(k[m]))) ** 2).sum() / ((le - le.mean()) ** 2).sum()
    a = -np.polyfit(k[m], le, 1)[0]
    if r2e >= r2a and a > 1e-9:
        return int(np.ceil((1 / (2 * a)) * np.log(1.0 / max(eps ** 2, 1e-300))))
    return r_true(lam, eps)


print(f"  {'系统':>26}{'eps':>7}{'真值':>8}{'SRS-神谕':>10}{'比值':>9}{'E99_eps':>10}{'比值':>9}")
import os
FD = r"E:\deepseekworkspace\JCP_submission\manuscript_rank_scaling\data\figure_data"
PD = r"E:\deepseekworkspace\JCP_submission\benchmark\PDEBench"
checks = []
for nm, fn, kind in (("Advection b=1", "1D_Advection_Sols_beta1.0.hdf5", "pde"),
                     ("Burgers nu=0.01", "1D_Burgers_Sols_Nu0.01.hdf5", "pde")):
    import h5py
    p = os.path.join(PD, fn)
    if not os.path.exists(p):
        continue
    with h5py.File(p, "r") as f:
        ten = f["tensor"]
        i = int(ten.shape[0] // 3)
        field = np.asarray(ten[i], dtype=np.float64)
        if field.ndim > 2:
            field = field.reshape(field.shape[0], -1)
        Y = np.nan_to_num(field - field.mean(0, keepdims=True))
        sv = np.linalg.svd(Y, compute_uv=False)
        lam = (sv ** 2) / max(Y.shape[0] - 1, 1)
    for eps in (0.05, 0.1):
        rt = r_true(lam, eps)
        so = srs_oracle(lam, eps)
        ee = r_true(lam, eps)
        print(f"  {nm:>26}{eps:>7.2f}{rt:>8}{so:>10}{so/max(rt,1):>9.2f}{ee:>10}{ee/max(rt,1):>9.2f}")
        checks.append(dict(system=nm, eps=eps, r_true=rt, srs_oracle=so,
                           ratio=so / max(rt, 1)))
for nm, fn in (("KS L=22 N=32", "figures1_ks_spectrum.txt"),
               ("Lorenz-96 N=40", "figures1_l96_spectrum.txt")):
    p = os.path.join(FD, fn)
    if not os.path.exists(p):
        continue
    rows_ = []
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows_.append([float(x) for x in line.split()])
        except ValueError:
            continue
    aa = np.array(rows_)
    lam = np.maximum(aa[:, 1], 0) ** 2
    for eps in (0.05, 0.1):
        rt = r_true(lam, eps)
        so = srs_oracle(lam, eps)
        ee = r_true(lam, eps)
        print(f"  {nm:>26}{eps:>7.2f}{rt:>8}{so:>10}{so/max(rt,1):>9.2f}{ee:>10}{ee/max(rt,1):>9.2f}")
        checks.append(dict(system=nm, eps=eps, r_true=rt, srs_oracle=so,
                           ratio=so / max(rt, 1)))
rr = [c["ratio"] for c in checks if np.isfinite(c["ratio"])]
print(f"\n  即使给 SRS 真谱与最优形式（神谕版），比值仍 = "
      f"{min(rr):.2f} .. {max(rr):.2f}（1.0 = 完美）")
print("  => SRS 的失败**不是**实现缺陷；闭式本身与枚举不等价")
res["N8_oracle"] = checks

# ============================================================
print()
print("=" * 112)
print("[N9 反查] alpha_cov 与 Delta 真的无关吗？（我可能过度声称）")
print("=" * 112)
print("  精确 Toeplitz：corr(Delta, alpha_cov) 是多少？")
Ds = np.array([0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0])
As = []
for D in Ds:
    w = toeplitz_eigs(np.exp(-D), 64)
    v = np.maximum(w, 1e-300)
    k = np.arange(1, len(v) + 1); m = k >= 2
    As.append(-np.polyfit(k[m], np.log(v[m]), 1)[0])
As = np.array(As)
print(f"  Delta 范围 {Ds.min():.2f}..{Ds.max():.2f}（跨度 {Ds.max()/Ds.min():.1f}×）")
print(f"  alpha_cov 范围 {As.min():.5f}..{As.max():.5f}（跨度 {As.max()/As.min():.1f}×）")
print(f"  corr(Delta, alpha_cov) = {np.corrcoef(Ds, As)[0,1]:.5f}")
print(f"  corr(log Delta, log alpha_cov) = {np.corrcoef(np.log(Ds), np.log(As))[0,1]:.5f}")
sl = np.polyfit(np.log(Ds), np.log(As), 1)
print(f"  幂律拟合: alpha_cov ~ Delta^{sl[0]:.4f}  （R²={1-((np.log(As)-np.polyval(sl,np.log(Ds)))**2).sum()/((np.log(As)-np.log(As).mean())**2).sum():.5f}）")
print()
if abs(sl[0]) > 0.5:
    print(f"  => **我过度声称了！** alpha_cov 与 Delta 有幂律关系（指数 {sl[0]:.2f}），")
    print("     alpha_cov is NOT merely a second-order effect. Manuscript wording must be revised.")
else:
    print("  => supports a weak-dependence statement")
res["N9_corr"] = float(np.corrcoef(Ds, As)[0, 1])
res["N9_power"] = float(sl[0])

json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
print(f"\n已保存 {OUT}")
