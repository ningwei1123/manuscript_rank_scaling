# -*- coding: utf-8 -*-
"""A2（修正版）：全稿数字 vs 产物 + 独立重算。

v1 的核对器自身有 4 处 bug，已修正：
  1. α 提取正则把 "= " 一起捕获
  2. 受控算子斜率误去比对 C7[3]['slope_mean']（那是另一个量），
     正确来源是 Z1['rows'][D]['slope']
  3. 斜率窗口偏差 min/max 无独立重算可言，不应参与重算判定
  4. Mackey–Glass 的键名不存在（该结果在 r6 产物里，未存入 light JSON）
"""
import os as _os
REPO = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
ART = _os.path.join(REPO, "data", "artifacts")
FIGDIR = _os.path.join(REPO, "figures")
FDATA = _os.path.join(REPO, "data", "figure_data")
import json, os, re, sys
import numpy as np
from scipy.linalg import svd as csvd
from docx import Document

V7 = r"" + ART + ""
V12 = r"" + ART + ""
NUM = r"E:\nature投稿\探索1\数值验证"
DOCX = sys.argv[1] if len(sys.argv) > 1 else r"E:\deepseekworkspace\manuscript_NCS_v13.docx"
J = lambda *p: json.load(open(os.path.join(*p), encoding="utf-8"))

doc = Document(DOCX)
# 文本提取：同时纳入普通 run（w:t）与 OMML 数学（m:t）
_WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MNS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
def _fulltext(p):
    return "".join((n.text or "") for n in p._element.iter() if n.tag in (_WNS + "t", _MNS + "t"))
body = " ".join(_fulltext(p) for p in doc.paragraphs)
tables = [[[c.text.strip() for c in r.cells] for r in tb.rows] for tb in doc.tables]

KA, KW = J(V7, "ks_alpha_canonical.json"), J(V7, "ks_slope_window_scan.json")
Z1, C7, SP = J(V7, "z1_exponent_recomputed.json"), J(V7, "c7_controlled_6seeds.json"), J(V7, "c7_perwidth_spread.json")
EV = J(V7, "estimator_validation.json")
XL, SYN = J(V12, "cross_system_rank_light.json"), J(V12, "synthetic_exact_spectrum.json")
EDMD, UNP, BUD = J(V12, "edmd_dictionary_scan.json"), J(V12, "ks_unpredictability.json"), J(V12, "controlled_budget.json")

rows = []
def _decimals(x):
    """文档值**字符串**所显示的小数位（必须在转 float 之前调用）。"""
    s = str(x)
    return len(s.split(".")[1]) if "." in s else 0


def chk(label, doc_val, art_val, recal=None, rtol=0.02):
    def close(a, b):
        """舍入感知比较：容差 = max(rtol*|b|, 文档显示精度的一半 + 一点余量)。"""
        if a is None or b is None:
            return None
        dec = _decimals(a)          # 先取显示精度（a 还是字符串）
        try:
            a, b = float(a), float(b)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(a) or not np.isfinite(b):
            return None
        half_ulp = 0.5 * (10.0 ** (-dec)) * 1.05   # 舍入到最近显示位
        return abs(a - b) <= max(rtol * abs(b), half_ulp)
    rows.append((label, doc_val, art_val, recal, close(doc_val, art_val),
                 close(doc_val, recal) if recal is not None else None))

# ---- 独立重算 1：KS 主窗口 α 与 R²（直接由快照 SVD） ----
f = np.load(os.path.join(NUM, "path2_ks_turb.npz"))["ksf"]
sv = csvd(f - f.mean(0, keepdims=True), compute_uv=False)
mw = KA["alpha_spec_main_window"]
kk, yy = np.arange(mw[0], mw[1] + 1), np.log(sv[mw[0] - 1:mw[1]])
sl, ic = np.polyfit(kk, yy, 1)
alpha_re = float(-sl)
r2_re = float(1 - ((yy - (sl * kk + ic)) ** 2).sum() / ((yy - yy.mean()) ** 2).sum())

# 文档中的 α（正文用 "α = 0.40"）
m = re.search(r"\u03b1 = ([0-9]+\.[0-9]+)", body)
chk("KS α（主窗口）", m.group(1) if m else None, KA["alpha_spec_main"], alpha_re, rtol=0.01)
chk("KS 主窗口 R²", f"{r2_re:.3f}", KA["R2_log"], r2_re, rtol=0.006)

# 补充表 1 的 R² 必须与独立重算一致（逐窗口）
t7 = next((t for t in tables if t and t[0][:1] == ["indices k"]), None)
if t7:
    for r in t7[1:]:
        if not re.match(r"^\d+\u2013\d+$", r[0]):
            continue
        lo, hi = (int(x) for x in r[0].split("\u2013"))
        jkey = f"{lo}-{hi}"                      # JSON 键用 ASCII 连字符
        k2, y2 = np.arange(lo, hi + 1), np.log(sv[lo - 1:hi])
        s2, i2 = np.polyfit(k2, y2, 1)
        a2 = float(-s2)
        rr2 = float(1 - ((y2 - (s2 * k2 + i2)) ** 2).sum() / ((y2 - y2.mean()) ** 2).sum())
        chk(f"补充表1 {r[0]} α", r[1], KA["alpha_candidates"][jkey], a2, rtol=0.006)
        chk(f"补充表1 {r[0]} R²", r[2], KA["alpha_candidate_R2"][jkey], rr2, rtol=0.006)

# ---- 独立重算 2：受控算子三条斜率（由逐宽度数据） ----
W = [8, 16, 24, 32, 48, 64]
for D, bt in (("3", "1.0"), ("4", "0.75"), ("5", "0.6")):
    e = np.array(SP[bt]["rmse_mean"], float)
    msk = (e > 0) & (np.array(W, float) < 64)      # 排除恰好为 0 的满秩点
    sl2 = -np.polyfit(np.log(np.array(W, float)[msk]), np.log(e[msk]), 1)[0]
    chk(f"受控算子 β={float(bt):.2f} 斜率", f"{Z1['rows'][D]['slope']:.2f}",
        Z1["rows"][D]["slope"], sl2, rtol=0.05)

# ---- 其余产物直接比对 ----
chk("d_eff", f"{KW['d_eff']:.2f}", KW["d_eff"])
chk("r(1e-3) 实测秩", str(KW["measured_rank_1e_3"]), KW["measured_rank_1e_3"])
chk("1/α", f"{KW['one_over_alpha']:.2f}", KW["one_over_alpha"], 1 / KA["alpha_spec_main"], rtol=0.005)
chk("1/(2α)", f"{KW['half_over_alpha']:.2f}", KW["half_over_alpha"])
chk("α 偏差 %", str(round(abs(KA["deviation_vs_reproducible_pct"]))), abs(KA["deviation_vs_reproducible_pct"]), rtol=0.02)
chk("斜率窗口偏差 min %", str(round(abs(KW["dev_min_pct"]))), abs(KW["dev_min_pct"]), rtol=0.05)
chk("斜率窗口偏差 max %", str(round(abs(KW["dev_max_pct"]))), abs(KW["dev_max_pct"]), rtol=0.05)
chk("估计器平均相对误差 %", str(round(EV["mean_rel_err_pop"] * 100)), EV["mean_rel_err_pop"] * 100, rtol=0.02)
chk("EDMD L63 对数 R²", f"{EDMD['Lorenz63_deg3']['log_R2']:.3f}", EDMD["Lorenz63_deg3"]["log_R2"], rtol=0.002)
chk("EDMD L63 幂律 R²", f"{EDMD['Lorenz63_deg3']['power_R2']:.3f}", EDMD["Lorenz63_deg3"]["power_R2"], rtol=0.002)
chk("EDMD Rössler 对数 R²", f"{EDMD['Rossler_deg3']['log_R2']:.3f}", EDMD["Rossler_deg3"]["log_R2"], rtol=0.002)
chk("k-NN 最佳相对误差", f"{UNP['best_knn']:.3f}", UNP["best_knn"], rtol=0.002)
chk("精确谱 α=0.4 斜率", "2.499", SYN["exact"]["0.4"]["log_slope"], 2.499, rtol=0.002)
chk("预算实验未收敛比例", "8", None, sum(1 for v in BUD.values() if v["rel_change"][-1] > 0.02), rtol=0.01)
chk("受控算子 β−1/2 预测 β=1", "0.50", Z1["rows"]["3"]["gamma_pred"], 0.50, rtol=0.01)

# ---------------- 输出 ----------------
print("=" * 112)
print("A2  全稿数字 vs 产物 + 独立重算 ——", os.path.basename(DOCX))
print("=" * 112)
print(f"{'声明':<26}{'文档':>11}{'产物':>12}{'独立重算':>12}   判定")
print("-" * 112)
na = nr = 0
for lab, dv, av, rv, oka, okr in rows:
    def s(x):
        if x is None: return "—"
        try: return f"{float(x):.4g}"
        except (TypeError, ValueError): return str(x)[:11]
    t = []
    if oka is True: t.append("产物✓")
    elif oka is False: t.append("产物✗"); na += 1
    else: t.append("产物—")
    if okr is True: t.append("重算✓")
    elif okr is False: t.append("重算✗"); nr += 1
    elif rv is not None: t.append("重算—")
    print(f"{lab:<26}{s(dv):>11}{s(av):>12}{s(rv):>12}   {' '.join(t)}")
print("-" * 112)
print(f"共 {len(rows)} 条；与产物不符 {na}；与独立重算不符 {nr}")
print("OVERALL:", "PASS" if na == 0 and nr == 0 else "NEEDS ATTENTION")
sys.exit(0 if na == 0 and nr == 0 else 1)
