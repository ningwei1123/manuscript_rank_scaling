# -*- coding: utf-8 -*-
"""Crossref 验证 33 条参考文献的真实性。
策略：① 有 DOI 的直接查 DOI；② 无 DOI 的用标题+作者查 Crossref bibliographic query。
输出：每条的状态（验证通过 / DOI 不符 / 查无此项）+ Crossref 返回的权威元数据。
"""
import io, re, json, time, urllib.parse, urllib.request
from docx import Document

P = r"E:\deepseekworkspace\manuscript_JCP_v41.docx"
d = Document(P)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def fe(el):
    return "".join((n.text or "") for n in el.iter() if n.tag in (W + "t", M + "t"))


ps = [fe(p._element).strip() for p in d.paragraphs]
iRef = ps.index("References")
REFS = {}
for t in ps[iRef + 1:]:
    m = re.match(r'^(\d+)\.\s+(.*)$', t)
    if m:
        REFS[int(m.group(1))] = m.group(2)

print(f"提取 {len(REFS)} 条参考文献\n")

UA = "Mozilla/5.0 (compatible; reference-check/1.0; mailto:ningwei@snut.edu.cn)"


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return {"__error__": str(e)}
            time.sleep(2)
    return {"__error__": "unknown"}


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


results = {}
for n in sorted(REFS):
    raw = REFS[n]
    doi = None
    m = re.search(r'10\.\d{4,9}/[^\s,;)\]]+', raw)
    if m:
        doi = m.group(0).rstrip(".")
    # 粗提标题：去掉作者与年份部分
    title_guess = raw
    title_guess = re.sub(r'^.*?\(\d{4}[a-z]?\)\.\s*', '', title_guess) if re.search(r'\(\d{4}[a-z]?\)\.', title_guess) else title_guess
    rec = {"n": n, "raw": raw, "doi": doi}

    if doi:
        j = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
        if "__error__" in j:
            rec["status"] = "DOI 查询失败"
            rec["err"] = j["__error__"]
        else:
            msg = j.get("message", {})
            rec["status"] = "DOI 有效"
            rec["cr_title"] = strip_html((msg.get("title") or [""])[0])
            rec["cr_year"] = (msg.get("issued", {}).get("date-parts") or [[None]])[0][0]
            rec["cr_journal"] = strip_html((msg.get("container-title") or [""])[0])
            rec["cr_type"] = msg.get("type")
    else:
        q = urllib.parse.urlencode({"query.bibliographic": raw[:300], "rows": 3})
        j = get("https://api.crossref.org/works?" + q)
        if "__error__" in j:
            rec["status"] = "查询失败"
            rec["err"] = j["__error__"]
        else:
            items = j.get("message", {}).get("items", [])
            rec["status"] = "标题查询"
            rec["candidates"] = [
                {"title": strip_html((it.get("title") or [""])[0]),
                 "doi": it.get("DOI"),
                 "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
                 "journal": strip_html((it.get("container-title") or [""])[0]),
                 "score": it.get("score")}
                for it in items]
    results[n] = rec
    print(f"[{n:>2}] {rec['status']:<14} {raw[:88]}")
    time.sleep(0.6)

io.open(r"E:\deepseekworkspace\crossref_results.json", "w", encoding="utf-8").write(
    json.dumps(results, ensure_ascii=False, indent=1))
print("\n已保存 crossref_results.json")
