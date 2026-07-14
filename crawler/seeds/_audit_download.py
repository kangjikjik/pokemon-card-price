"""문제 세트 이미지 다운로드 + pokemoncard 페이지 후보 수집"""
from __future__ import annotations

import re
from pathlib import Path

import httpx

from kr_sets import KR_BY_CODE
from resolve_legacy_box_images import DATA1_IMG, MAIN_IMG, PLACEHOLDER

OUT = Path(__file__).parent / "_img_audit"
OUT.mkdir(exist_ok=True)

CODES = [
    "SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM7a", "SM12", "SM12a",
    "S2", "S1W", "S1H", "SM2+", "SM1M", "SM1C", "XY8a",
    "SM6a", "SM10", "SM9a", "CP6", "MG6",
]

client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def safe(name: str) -> str:
    return re.sub(r"[^\w.+-]+", "_", name)


for code in CODES:
    s = KR_BY_CODE[code]
    url = s.box_image_kr
    ext = Path(url.split("?")[0]).suffix or ".png"
    path = OUT / f"{safe(code)}_CURRENT{ext}"
    try:
        r = client.get(url)
        path.write_bytes(r.content)
        print(f"saved {path.name} ({len(r.content)} bytes)")
    except Exception as e:
        print(f"FAIL {code}: {e}")

    if not s.pokemoncard_page:
        continue
    pr = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}")
    pr.encoding = "utf-8"
    html = pr.text
    # title
    m = re.search(r"<title>([^<]+)</title>", html)
    title = m.group(1).strip() if m else "?"
    print(f"\n=== {code} {s.name_kr} page={s.pokemoncard_page} title={title} ===")
    print(f"  current: {url}")

    imgs = []
    for u in DATA1_IMG.findall(html):
        if PLACEHOLDER not in u:
            imgs.append(u)
    for u in MAIN_IMG.findall(html):
        imgs.append(u)
    # also look for img tags with alt containing set name fragments
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.I):
        src = m.group(1)
        if "pokemonkorea" in src and PLACEHOLDER not in src:
            if src not in imgs:
                imgs.append(src)

    seen = set()
    uniq = []
    for u in imgs:
        if u not in seen:
            seen.add(u)
            uniq.append(u)

    for i, u in enumerate(uniq[:12]):
        print(f"  cand[{i}] {u}")
        try:
            ir = client.get(u)
            (OUT / f"{safe(code)}_c{i}_{safe(u.split('/')[-1])}").write_bytes(ir.content)
        except Exception:
            pass
