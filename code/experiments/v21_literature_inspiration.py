# -*- coding: utf-8 -*-
"""文献启发检索：为什么 E99 有效？新算法应利用什么原理？

E99 的事实（上一轮）：在 6 个真实系统上比例 0.67–1.00（永不严重高估）。
SRS 的失败：依赖"谱是单一参数形式"。

检索方向：
 · 有限样本谱估计的噪声地板（Marchenko-Pastur 型）
 · Kolmogorov n-width / 熵数给出的秩-精度关系
 · 有效秩（effective rank）的鲁棒定义
 · 熵 / 信息准则
"""
import io, os, re

D = r"E:\deepseekworkspace\lit_review"
PATS = {
 "有限样本噪声地板": [r"Marchenko", r"noise floor", r"bulk.{0,30}eigenvalue",
                r"sample.{0,30}eigenvalue.{0,30}bias", r"rank.{0,25}at most.{0,20}M"],
 "熵数 / n-width 秩-精度": [r"entropy number", r"n-width", r"Kolmogorov width",
                     r"approximation.{0,30}rank.{0,30}rate"],
 "有效秩鲁棒定义": [r"effective rank", r"stable rank", r"numerical rank",
             r"rank.{0,20}threshold"],
 "最优阈值 / 收缩": [r"optimal hard threshold", r"optimal shrinkage",
              r"singular value threshold", r"universal threshold"],
 "本征值估计误差界": [r"eigenvalue.{0,30}perturbation", r"Weyl.{0,20}inequality",
              r"Davis.Kahan", r"sin.?theta"],
}
for tag, pats in PATS.items():
    print("=" * 106)
    print(tag)
    print("=" * 106)
    hits = 0
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".txt"):
            continue
        s = io.open(os.path.join(D, fn), encoding="utf-8", errors="replace").read()
        for pat in pats:
            m = list(re.finditer(pat, s, re.I))
            if m:
                hits += 1
                h = m[0]
                a = max(0, h.start() - 150); b = min(len(s), h.end() + 320)
                print(f"  [{fn[:40]:<40}] {' '.join(s[a:b].split())[:300]}")
                break
    if not hits:
        print("  （无匹配）")
    print()
