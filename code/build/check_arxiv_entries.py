# -*- coding: utf-8 -*-
"""① 全部 arXiv 条目；② 重查 [16] 完整 DOI；③ 核对 [31] 标题。"""
import io, json, re, time, urllib.request, urllib.parse

R = json.load(io.open(r"E:\deepseekworkspace\crossref_results.json", encoding="utf-8"))
UA = "Mozilla/5.0 (compatible; reference-check/1.0; mailto:ningwei@snut.edu.cn)"


def gj(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return {"__error__": str(e)}
            time.sleep(2)


def gs(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                return f"__ERR__{e}"
            time.sleep(2)


print("=" * 110)
print("① 全部含 arXiv 的条目")
print("=" * 110)
for n in sorted(R, key=lambda x: int(x)):
    for m in re.finditer(r'arXiv:\s*(\d{4}\.\d{4,5})', R[n]["raw"]):
        aid = m.group(1)
        body = gs(f"https://arxiv.org/abs/{aid}")
        if body.startswith("__ERR__"):
            print(f"  [{n:>2}] arXiv:{aid}  **获取失败**")
        else:
            t = re.search(r'<title>(.*?)</title>', body, re.S)
            title = re.sub(r'\s+', ' ', t.group(1)).strip() if t else "?"
            print(f"  [{n:>2}] arXiv:{aid}  存在")
            print(f"        {title[:104]}")
        time.sleep(1.0)

print("\n" + "=" * 110)
print("② 重查 [16] 完整 DOI")
print("=" * 110)
d16 = "10.1016/0022-0396(83)90011-6"
j = gj("https://api.crossref.org/works/" + urllib.parse.quote(d16, safe=""))
if "__error__" in j:
    print(f"  {d16}  ->  {j['__error__']}")
else:
    msg = j["message"]
    print(f"  DOI: {d16}  有效")
    print(f"  标题: {(msg.get('title') or [''])[0]}")
    print(f"  刊/年: {(msg.get('container-title') or [''])[0]} / {(msg.get('issued',{}).get('date-parts') or [[None]])[0][0]}")
    print(f"  卷/页: {msg.get('volume')} / {msg.get('page')}")

print("\n" + "=" * 110)
print("③ 核对 [31] Benettin 的标题")
print("=" * 110)
for doi in ("10.1007/BF02128236", "10.1007/BF02128237"):
    j = gj("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    if "__error__" in j:
        print(f"  {doi}: {j['__error__']}")
    else:
        msg = j["message"]
        print(f"  {doi}: {(msg.get('title') or [''])[0][:100]}")
        print(f"        {(msg.get('container-title') or [''])[0]} {msg.get('volume')}, {msg.get('page')} ({(msg.get('issued',{}).get('date-parts') or [[None]])[0][0]})")
