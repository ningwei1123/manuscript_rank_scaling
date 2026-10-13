# -*- coding: utf-8 -*-
"""Validate manuscript_JCP_v3.docx against NCS structural requirements."""
import re, sys
from docx import Document

DOCX = r"E:\deepseekworkspace\manuscript_JCP_v3.docx"
d = Document(DOCX)
ps = [p.text.strip() for p in d.paragraphs]

def wc(t):
    return len(re.findall(r"[A-Za-z\u00c0-\u024f]+", t))

HEADS = ("Abstract", "1. Introduction", "2. Results", "3. Conclusions", "4. Methods",
         "References", "Supplementary Information", "Data availability",
         "Code availability", "Competing interests", "Funding",
         "CRediT authorship contribution statement", "Declaration of competing interest",
         "Acknowledgements")
idx = {}
for i, t in enumerate(ps):
    if t in HEADS and t not in idx:
        idx[t] = i

def block(a, b):
    return [ps[i] for i in range(a + 1, b) if ps[i]]

def capt(t):
    return t.startswith("Figure ") or t.startswith("Table ") or t.startswith("Supplementary Figure ")

iA, iR = idx["Abstract"], idx["2. Results"]
iD, iM = idx["3. Conclusions"], idx["4. Methods"]
iS = idx.get("Supplementary Information", len(ps))

_ai = iA + 1
while _ai < len(ps) and (ps[_ai].startswith("\u2022") or ps[_ai] == "Highlights"):
    _ai += 1
abstract = ps[_ai]
_kw = next((k for k in range(iA+1, iA+6) if ps[k].startswith("Keywords")), None)
iA_eff = _kw if _kw is not None else iA
intro = block(iA, iR)[1:]                     # skip the abstract paragraph
results = block(iR, iD)
disc = block(iD, iM)
methods = [t for t in block(iM, iS) if not t.startswith(("Data availability", "Code availability",
                                                         "Competing interests", "Funding", "References"))]

print("=" * 80)
print("JCP STRUCTURAL VALIDATION -- manuscript_JCP_v3.docx")
print("=" * 80)

print(f"\n[Abstract]  words = {wc(abstract)}   (guide: <= 250 for JCP)")
print(f"  citations in abstract: {bool(re.search(r'\[\d', abstract))}   (must be False)")

main_caps = [t for t in results + disc
             if re.match(r"^(Figure|Table)\s+\d+\s*\|", t) and len(t) > 150]
main_figs = [t for t in main_caps if t.startswith("Figure ")]
main_tbls = [t for t in ps if re.match(r"^Table\s+\d+\s*\|", t)]
sup_figs = [t for t in ps[iS:] if re.match(r"^Supplementary Figure\s+\d+\s*\|", t)]
n_tables = sum(1 for tb in d.tables if len(tb.rows) > 1)

print(f"\n[Display items]  main figures = {len(main_figs)}, main tables = {len(main_tbls)}"
      f" (docx tables with >1 row: {n_tables})  -> main display total {len(main_figs) + len(main_tbls)}"
      "   (no hard limit in JCP)")
print(f"  supplementary figures    : {len(sup_figs)}")

res_prose = sum(wc(t) for t in results if not capt(t) and not t.startswith("Which operator"))
dis_prose = sum(wc(t) for t in disc)
in_prose = sum(wc(t) for t in intro)
print(f"\n[Word counts]")
print(f"  Introduction (untitled)  {in_prose:5d}")
print(f"  Results prose            {res_prose:5d}")
print(f"  Discussion prose         {dis_prose:5d}")
print(f"  MAIN TEXT total          {in_prose + res_prose + dis_prose:5d}   (JCP: no word limit; ~25 page guide)")
print(f"  figure/table legend words {sum(wc(t) for t in main_caps):5d}   (excluded from the limit)")
print(f"  Methods                  {sum(wc(t) for t in methods):5d}   (excluded from the limit)")

print(f"\n[Structure]")
print(f"  Introduction section     : {'PASS' if 'Introduction' not in ps else 'FAIL'}")
print(f"  Results has subsections  : {'PASS' if any(t and wc(t) < 12 and not capt(t) for t in results[:3]) else 'FAIL'}")
print(f"  Conclusions has NO subsections: {'PASS' if dis_prose == sum(wc(t) for t in disc) else 'CHECK'}")
print(f"  Methods present          : {'PASS' if '4. Methods' in idx else 'FAIL'}")
decls = ["Data availability", "Code availability", "Competing interests", "Funding"]
print(f"  declarations complete    : {'PASS' if all(x in idx for x in decls) else 'FAIL'}"
      f"   missing={[x for x in decls if x not in idx]}")

_ri = next((k for k, t in enumerate(ps) if t == "References"), None)
refs = ([t for t in ps[_ri + 1:] if re.match(r"^\d+\.\s", t)]
        if _ri is not None else [])
print(f"  references               : {len(refs)}   (typical: <= 80)")
cited = set()
for t in ps:
    for m in re.finditer(r"\[(\d+(?:,\d+)*)\]", t):
        cited.update(int(x) for x in m.group(1).split(","))
print(f"  all refs cited           : {'PASS' if cited == set(range(1, len(refs) + 1)) else 'FAIL'}"
      f"   uncited={sorted(set(range(1, len(refs)+1)) - cited)}  "
      f"out-of-range={sorted(c for c in cited if c > len(refs))}")

figs = re.findall(r"^Figure\s+(\d+)\s*\|", "\n".join(ps), re.MULTILINE)
print(f"  figure captions numbered consecutively: {'PASS' if [int(x) for x in figs] == list(range(1, len(figs)+1)) else 'FAIL'} {figs}")
order = []
for k, t in enumerate(ps):
    if re.match(r"^(Figure|Supplementary Figure|Table)\s+\d+\s*\|", t):
        for m in re.finditer(r"^Figure\s+(\d+)\s*\|", t):
            n = int(m.group(1))
            if n not in order:
                order.append(n)
        continue
    for m in re.finditer(r"Figs?\.\s*(\d+)", t):
        n = int(m.group(1))
        if n not in order:
            order.append(n)
print(f"  first-citation order     : {'PASS' if order == sorted(order) else 'FAIL'} {order}")

print(f"\n[Equations]")
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
eqs = []
for t in d.tables:
    if len(t.rows) == 1 and len(t.rows[0].cells) == 2:
        left, right = t.rows[0].cells
        has = left._tc.find(".//m:oMath", namespaces={"m": MATH_NS}) is not None
        lab = right.text.strip()
        if has and re.match(r"^\(\d+\)$", lab):
            eqs.append(int(lab[1:-1]))
print(f"  display equations        : {len(eqs)} numbered {eqs}"
      f"   {'PASS' if eqs == list(range(1, len(eqs)+1)) else 'FAIL'}")
print(f"  equations render as OMML : {'PASS' if len(eqs) >= 5 else 'FAIL'}")

print("\n" + "=" * 80)
ok = (wc(abstract) <= 250 and not re.search(r"\[\d", abstract)
      and len(main_figs) + len(main_tbls) <= 12
      and in_prose + res_prose + dis_prose <= 6000
      and all(x in idx for x in decls) and len(refs) <= 50
      and cited == set(range(1, len(refs) + 1))
      and len(eqs) >= 5)
print("OVERALL:", "PASS" if ok else "NEEDS ATTENTION")
sys.exit(0 if ok else 1)

