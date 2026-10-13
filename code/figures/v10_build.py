# -*- coding: utf-8 -*-
"""v10：落实第八轮 Z1、Z1-a、Y6、Y7 与次要项。"""
import shutil, ast, os, json

WS = r"E:\deepseekworkspace"
BASE = os.path.join(WS, "ncs_v6", "make_manuscript_v9.py")
P = os.path.join(WS, "ncs_v6", "make_manuscript_v10.py")
BLK = os.path.join(WS, "ncs_v6", "v10_controlled_block.txt")
shutil.copyfile(BASE, P)
s = open(P, encoding="utf-8").read()
log = []
def sub(old, new, label):
    global s
    c = s.count(old)
    if c != 1:
        log.append("FAIL %s (%d)" % (label, c)); return
    s = s.replace(old, new, 1); log.append("ok   " + label)

# ---------- 输出名 ----------
sub('OUT = r"E:\\deepseekworkspace\\manuscript_NCS_v9.docx"',
    'OUT = r"E:\\deepseekworkspace\\manuscript_NCS_v10.docx"', "输出 -> v10")

# ---------- 载入 Z1 更正数据 ----------
old_load = '_KA = json.load(open(r"E:\\deepseekworkspace\\experiments_v7\\ks_alpha_canonical.json",'
new_load = ('_Z1 = json.load(open(r"E:\\deepseekworkspace\\experiments_v7\\z1_exponent_recomputed.json",\n'
            '                     encoding="utf-8"))\n' + old_load)
sub(old_load, new_load, "载入 z1 数据")

# ---------- Z1：受控算子段整段替换（模板）----------
i0 = s.find('P([\n "On the controlled operators')
if i0 < 0:
    i0 = s.find(' "On the controlled operators')
    i0 = s.rfind('P([', 0, i0)
i1 = s.find('], after=4)', i0)
i2 = s.find('FIG("Fig5_width_law.png"', i1)
if i0 < 0 or i1 < 0 or i2 < 0:
    log.append("FAIL Z1 段定位 (i0=%d i1=%d i2=%d)" % (i0, i1, i2))
else:
    blk = open(BLK, encoding="utf-8").read().rstrip("\n")
    s = s[:i0] + blk + "\n\n" + s[i2:]
    log.append("ok   Z1 受控算子段整段替换")

# ---------- Z1：Fig 3 图注改为指数对指数 ----------
sub('"network averaged over six seeds. b, Measured and exact error\\u2013width exponents; the measured "',
    '"network averaged over six seeds. b, Measured error\\u2013width exponents against the predicted "\n'
    '    "exponents. The prediction is \\u03b2 \\u2212 1/2 under the Frobenius convention used for the reference "\n'
    '    "curve in a, and \\u03b2 under the operator-norm convention; the measured exponents rise as \\u03b2 "\n'
    '    "falls while both predictions fall, so the ordering is not resolved. The values "',
    "Z1 Fig3 图注")

# ---------- Z1-a：估计量段的 alpha 口径 ----------
sub('"with M, the decay rate from \\u03b1 = " + f"{_EV[\'rows\'][0][\'alpha\']:.1f}"'
    ' + " at M = 200 to \\u03b1 = "',
    '"with M, the fitted decay rate from " + f"{_EV[\'rows\'][0][\'alpha\']:.1f}"'
    ' + " at M = 200 to "',
    "Z1-a 措辞 1")
sub('+ f"{_EV[\'rows\'][-1][\'alpha\']:.2f}" + " at M = 100,000, and the intercept from "',
    '+ f"{_EV[\'rows\'][-1][\'alpha\']:.2f}" + " at M = 100,000. That value is an alpha_rank, extracted "\n'
    ' "from the rank\\u2013accuracy curve of the fitted operator, not a direct spectral fit; it agrees with "\n'
    ' "the rank\\u2013accuracy estimate above (0.49) and exceeds the direct spectral value of "\n'
    ' + f"{A_KS:.2f}" + " by " + f"{abs(1/A_KS - 1/(1/_EV[\'rows\'][-1][\'alpha\']))/ (1/A_KS)*100:.0f}%"\n'
    ' + " in slope terms, the same discrepancy as in the rank\\u2013accuracy comparison. The intercept runs from "',
    "Z1-a alpha 口径")

# ---------- Z1-a：说明 0.71 -> 0.40 是纠错而非换窗 ----------
sub('"Kuramoto\\u2013Sivashinsky spectrum is not a single exponential. The rank\\u2013accuracy curve implies its "',
    '"Kuramoto\\u2013Sivashinsky spectrum is not a single exponential. This value supersedes the "\n'
    ' "\\u03b1 = 0.71 used in earlier versions. That number came from a fit restricted to singular values "\n'
    ' "above a numerical floor, which on this data retained only the near-saturated tail, and it cannot "\n'
    ' "be reproduced from the same data with the window it was labelled with; it is therefore a "\n'
    ' "correction, not a change of window, and the window scan is recorded in Supplementary Table 1 so "\n'
    ' "that the sensitivity can be checked. The rank\\u2013accuracy curve implies its "',
    "Z1-a 纠错说明")

# ---------- Y6-b：天花板图号统一为 Sup Fig. 1b ----------
sub('"finite-sample ceiling of Supplementary Fig. 6 rather than decoupling from the ambient dimension, "',
    '"finite-sample ceiling of Supplementary Fig. 1b rather than decoupling from the ambient dimension, "',
    "Y6 天花板图号")

# ---------- Y6-c：Sup Fig.5 图注移出主文 ----------
i = s.find('FIG("Fig3_dky_estimation.png",')
if i < 0:
    log.append("FAIL 参数恢复图未找到")
else:
    j = s.find('width_in=5.6)', i) + len('width_in=5.6)')
    blk2 = s[i:j]
    s = s[:i] + s[j:]                      # 从主文移除
    anchor = 'FIG("Fig2_rank_law.png",\n    "Supplementary Figure 6 |'
    k = s.find(anchor)
    if k < 0:
        log.append("FAIL SI 锚点未找到")
    else:
        s = s[:k] + blk2 + "\n" + s[k:]    # 插入 SI 开头
        log.append("ok   Sup Fig.5 图注移入 SI")

# ---------- Y6-b：Methods 中 Table 1 引用 ----------
sub('"this paper it is this one, and the two are labelled distinctly in Table 1 and Supplementary Fig. 5."',
    '"this paper it is this one, and the two are labelled distinctly in Table 1 and Supplementary Fig. 5, "\n'
    ' "which also lists the Kaplan\\u2013Yorke gap and the top gap for each system."',
    "Y6 Methods Table1 引用")

# ---------- 次要：cut-off 30 与饱和说明（图注）----------
sub('"energy convention 1/(2\\u03b1); the window is therefore reported rather than concealed.",',
    '"energy convention 1/(2\\u03b1); the window is therefore reported rather than concealed. The cut-off "\n'
    '    "of 30 lies close to the 32-mode ceiling, so the upper end of this range may carry a saturation "\n'
    '    "artefact; the canonical value uses ranks up to 22, below that knee.",',
    "次要 cut-off 饱和说明")

open(P, "w", encoding="utf-8").write(s)
print("\n".join(log))
nf = sum(1 for l in log if "FAIL" in l)
print("\n成功 %d，失败 %d" % (len(log) - nf, nf))
ast.parse(s); print("语法 OK")
