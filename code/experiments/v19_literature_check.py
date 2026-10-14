# -*- coding: utf-8 -*-
"""文献严格检验：针对稿件 v18 的每条关键主张，检索本机文献中的支持/冲突证据。

主张清单：
  C1. Koopman 算子在保测系统上酉 -> 无衰减谱；衰减属于协方差算子 C
  C2. 秩-精度关系 r(eps) ~ (1/alpha) log(1/eps)（指数谱）
  C3. 可达误差 = 输出协方差谱尾部（新定理）
  C4. 宽度律不可能是幂律（Lanthaler-Stuart 诅咒）
  C5. alpha 与 Lyapunov 隙无闭式联系（两个 alpha 不同）
  C6. 谱秩选择可省 20x 计算（SRS）
  C7. 低秩假设（Thibeault）是否与秩律竞争
"""
import io, os, re

D = r"E:\deepseekworkspace\lit_review"
FILES = sorted(f for f in os.listdir(D) if f.endswith(".txt"))

CLAIMS = {
 "C1 Koopman酉/无衰减谱": [
   r"Koopman.{0,60}unitar", r"unitar.{0,60}Koopman",
   r"isometr", r"no decay", r"spectrum.{0,30}unit circle",
 ],
 "C2 秩-精度对数律": [
   r"rank.{0,50}log", r"logarithmic.{0,40}rank",
   r"(1/alpha).{0,20}log", r"spectral decay.{0,50}(rank|dimension)",
 ],
 "C3 可达误差=输出谱尾部": [
   r"Eckart", r"Young", r"best rank", r"low.rank approxim",
   r"tail.{0,40}covariance",
 ],
 "C4 宽度律/参数复杂度诅咒": [
   r"curse of parametric", r"exponential.{0,40}(width|parameter)",
   r"n-width", r"Barron",
 ],
 "C5 alpha vs Lyapunov 隙": [
   r"Lyapunov gap", r"spectral gap.{0,50}Lyapunov",
   r"resonance.{0,40}gap",
 ],
 "C6 秩选择/降阶": [
   r"rank selection", r"rank truncation", r"model order",
   r"energy criterion", r"cross.validat",
 ],
 "C7 低秩假设": [
   r"low.rank hypothesis", r"low.rank.{0,40}(effective|dimensional)",
   r"effective dimension",
 ],
}

for tag, pats in CLAIMS.items():
    print("=" * 108)
    print(tag)
    print("=" * 108)
    hits = 0
    for fn in FILES:
        s = io.open(os.path.join(D, fn), encoding="utf-8", errors="replace").read()
        for pat in pats:
            m = list(re.finditer(pat, s, re.I))
            if m:
                hits += 1
                h = m[0]
                a = max(0, h.start() - 110)
                b = min(len(s), h.end() + 190)
                print(f"  [{fn[:42]:<42}] {' '.join(s[a:b].split())[:250]}")
                break
    if hits == 0:
        print("  （无匹配）")
    print()
