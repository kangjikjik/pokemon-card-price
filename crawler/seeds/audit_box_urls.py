"""kr_sets 박스 URL HTTP 검증 + pokemoncard 페이지 이미지 후보"""
from __future__ import annotations

import httpx
import re

from kr_sets import KR_SETS
from resolve_legacy_box_images import pick_box, DATA1_IMG, MAIN_IMG, PLACEHOLDER

BAD_KEYWORDS = ("banner", "hover", "bg_", "collection", "info_", "card_info", "gms05")

client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

print(f"{'code':6} | http | bad_kw | stored_tail")
print("-" * 80)
issues = []
for s in KR_SETS:
    url = s.box_image_kr or ""
    http = "?"
    if url:
        try:
            r = client.head(url)
            http = str(r.status_code)
        except Exception as e:
            http = "err"
    bad = any(k in url.lower() for k in BAD_KEYWORDS)
    tail = url.split("/")[-1][:40] if url else ""
    flag = "ISSUE" if bad or http not in ("200", "301", "302") else "OK"
    if flag != "OK":
        issues.append(s.code)
    print(f"{s.code:6} | {http:4} | {bad!s:5} | {tail} | {flag}")

print(f"\nissues={len(issues)}: {issues}")

# problem sets from screenshot
for code in ["SM5+", "SM4+", "SM4", "SM4a", "SM7a"]:
    s = next(x for x in KR_SETS if x.code == code)
    r = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}")
    r.encoding = "utf-8"
    print(f"\n=== {code} page {s.pokemoncard_page} ===")
    print("stored:", s.box_image_kr)
    print("pick_box:", pick_box(r.text))
    data1 = [u for u in DATA1_IMG.findall(r.text) if PLACEHOLDER not in u]
    mains = MAIN_IMG.findall(r.text)
    for u in data1[:5]:
        print("  data1:", u)
    for u in mains[:3]:
        print("  main:", u)
