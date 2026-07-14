"""후보 이미지 시각 검증용 다운로드 — 문제 세트만"""
from __future__ import annotations

from pathlib import Path

import httpx

OUT = Path(__file__).parent / "_img_audit"
OUT.mkdir(exist_ok=True)
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

# 단일 팩 후보로 의되는 URL들
CANDS = {
    "SM4_sun": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-05_19-58-16-29628-1515149896.png",
    "SM4_moon_alt": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-09_19-27-28-72312-1515493648.png",
    "SM4_dual": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png",
    "SM4_poster": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-09_19-29-12-23396-1515493752.jpg",
    "SM4_banner": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-24_11-15-48-50264-1516760148.png",
    "SM4a_pack": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "SM7a_c2": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-27_09-35-24-10929-1511742924.jpg",
    "SM7a_c6": "https://data1.pokemonkorea.co.kr/2017/12/2017-12-08_17-21-07-46128-1512721267.jpg",
    "SM7a_old": "https://data1.pokemonkorea.co.kr/2017/12/2017-12-13_10-44-40-86175-1513129480.jpg",
    "S1_c0": "https://data1.pokemonkorea.co.kr/2020/01/2020-01-21_18-35-45-24231-1579599345.png",
    "S1_c1": "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png",
    "S1_c2": "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-08-08-62477-1580796488.png",
    "S1_c3": "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-16-00-78026-1580796960.png",
    "S1_c4": "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-16-06-66296-1580796966.png",
    "SM1M_c0": "https://data1.pokemonkorea.co.kr/2017/01/2017-01-30_14-43-58-88992-1485755038.png",
    "SM1C_c2": "https://data1.pokemonkorea.co.kr/2017/02/2017-02-06_09-43-48-68758-1486341828.png",
    "SM1C_c6": "https://data1.pokemonkorea.co.kr/2017/02/2017-02-06_10-53-10-20216-1486345990.png",
    "SM1_tall": "https://data1.pokemonkorea.co.kr/2017/02/2017-02-13_10-16-01-29809-1486948561.jpg",
    "SM12_c1": "https://data1.pokemonkorea.co.kr/2019/10/2019-10-18_09-52-30-34519-1571359950.png",
    "SM12_c2": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-05_14-31-29-21178-1572931889.png",
    "SM12a_c0": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-27_14-54-21-95149-1574834061.png",
    "SM10_c1": "https://data1.pokemonkorea.co.kr/2019/05/2019-05-02_11-18-07-28354-1556763487.png",
    "SM9a_c0": "https://data1.pokemonkorea.co.kr/2019/01/2019-01-08_16-09-33-68309-1546931373.jpg",
    "SM9a_c11": "https://data1.pokemonkorea.co.kr/2019/01/2019-01-10_09-58-41-46178-1547081921.png",
    "SM6a_ok": "https://data1.pokemonkorea.co.kr/2018/06/2018-06-22_18-47-50-16043-1529660870.png",
    "CP6_c1": "https://data1.pokemonkorea.co.kr/2016/09/2016-09-20_14-05-53-64730-1474347953.jpg",
    "CP6_c5": "https://data1.pokemonkorea.co.kr/2016/09/2016-09-29_09-51-29-51182-1475110289.jpg",
    "SM5+_apr": "https://data1.pokemonkorea.co.kr/2018/04/2018-04-05_09-55-38-63937-1522889738.png",
    "SM2+_pack": "https://data1.pokemonkorea.co.kr/2017/10/2017-10-24_18-33-58-94770-1508837638.png",
}

for name, url in CANDS.items():
    ext = Path(url.split("?")[0]).suffix or ".png"
    path = OUT / f"cand_{name}{ext}"
    try:
        r = client.get(url)
        path.write_bytes(r.content)
        print(f"{name}: {len(r.content)} {path.name}")
    except Exception as e:
        print(f"{name}: FAIL {e}")

# collectory set images
print("\n=== collectory ===")
r = client.get("https://collectory.cc/api/sets")
sets = r.json().get("sets") or []
want = {
    "SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM7a", "SM12", "S2", "S1W", "S1H",
    "SM1M", "SM1C", "XY8a", "SM2+", "SM6a", "SM10", "SM9a", "SM12a", "CP6",
}
from kr_sets import KR_BY_CODE
for code in want:
    s = KR_BY_CODE[code]
    m = next((x for x in sets if x.get("id") == s.collectory_id), None)
    if m:
        img = m.get("image_url") or ""
        print(f"{code}: {img}")
        if img:
            try:
                ir = client.get(img)
                ext = Path(img.split("?")[0]).suffix or ".png"
                (OUT / f"col_{code}{ext}").write_bytes(ir.content)
            except Exception as e:
                print(f"  fail {e}")
    else:
        print(f"{code}: no collectory match id={s.collectory_id}")
