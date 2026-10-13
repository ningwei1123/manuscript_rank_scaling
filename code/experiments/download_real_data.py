# -*- coding: utf-8 -*-
"""下载真实观测数据到指定目录。

数据：
  1. HadISST1 海表温度（Met Office Hadley Centre，1870-至今，1° 网格）——真实观测
  2. NOAA OISST v2 月平均海表温度（1981-至今，1° 网格）——真实观测/卫星融合
  3. SILSO 太阳黑子月均（真实观测，1700-至今）
  4. NOAA Mauna Loa CO2 月均（真实观测）
  5. UAH 对流层温度异常（卫星观测）
"""
import os, io, ssl, gzip, time, urllib.request

DATA = r"E:\nature投稿\探索1\数据"
os.makedirs(DATA, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ITEMS = [
 ("HadISST1_sst.nc.gz", "https://www.metoffice.gov.uk/hadobs/hadisst/data/HadISST_sst.nc.gz"),
 ("OISSTv2_sst_mnmean.nc", "https://downloads.psl.noaa.gov/Datasets/noaa.oisst.v2/sst.mnmean.nc"),
 ("SILSO_sunspots_monthly.csv", "https://www.sidc.be/silso/DATA/SN_m_tot_V2.0.csv"),
 ("NOAA_MaunaLoa_CO2_monthly.csv", "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv"),
 ("UAH_tlt_6.0.txt", "https://www.nsstc.uah.edu/data/msu/v6.0/tlt/uahncdc_lt_6.0.txt"),
]


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


for fn, url in ITEMS:
    dst = os.path.join(DATA, fn)
    if os.path.exists(dst) and os.path.getsize(dst) > 10000:
        print(f"  [skip] {fn}  {os.path.getsize(dst)} B"); continue
    for attempt in range(3):
        try:
            d = fetch(url)
            io.open(dst, "wb").write(d)
            print(f"  [ok  ] {fn}  {len(d)/1048576:.2f} MB")
            break
        except Exception as e:
            if attempt == 2:
                print(f"  [FAIL] {fn}  {type(e).__name__}: {str(e)[:60]}")
            time.sleep(3)

print("\n=== 数据目录 ===")
for f in sorted(os.listdir(DATA)):
    p = os.path.join(DATA, f)
    print(f"  {os.path.getsize(p)/1048576:8.2f} MB  {f}")

# 解压 HadISST
gz = os.path.join(DATA, "HadISST1_sst.nc.gz")
nc = os.path.join(DATA, "HadISST1_sst.nc")
if os.path.exists(gz) and not os.path.exists(nc):
    try:
        with gzip.open(gz, "rb") as f, io.open(nc, "wb") as o:
            o.write(f.read())
        print(f"\n  已解压: HadISST1_sst.nc  {os.path.getsize(nc)/1048576:.2f} MB")
    except Exception as e:
        print(f"\n  解压失败: {type(e).__name__}: {e}")
