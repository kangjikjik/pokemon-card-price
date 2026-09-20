"""MG6 한국 공식 카드 이미지 URL 탐색 (pokemoncard.co.kr / pokemonkorea)."""
from __future__ import annotations

import json
import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://pokemoncard.co.kr/"}

# 포켓몬코리아 카드 DB API 후보
APIS = [
    "https://www.pokemonkorea.co.kr/api/v2/card/list?expansionCode=BS2026004",
    "https://www.pokemonkorea.co.kr/api/v2/cards?set=BS2026004",
    "https://pokemoncard.co.kr/api/card/list?pack=BS2026004",
    "https://pokemoncard.co.kr/api/cards?setCode=BS2026004",
]

for url in APIS:
    try:
        r = httpx.get(url, headers=HEADERS, timeout=20)
        print(f"\n{url} -> {r.status_code} len={len(r.text)}")
        if r.status_code == 200 and r.text.strip().startswith(("{", "[")):
            data = r.json()
            if isinstance(data, list):
                print(f"  list len={len(data)}")
                if data:
                    print("  sample keys:", list(data[0].keys())[:15])
            elif isinstance(data, dict):
                print("  keys:", list(data.keys())[:10])
    except Exception as e:
        print(f"\n{url} -> ERR {e}")

# pokemoncard 제품 페이지 HTML 분석
html = httpx.get("https://pokemoncard.co.kr/card/907", headers=HEADERS, timeout=30).text
print(f"\npokemoncard.co.kr/card/907 len={len(html)}")

# card image patterns
patterns = [
    r"https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg|webp)",
    r"https://[^\"'\s>]*pokemon[^\"'\s>]*\.(?:png|jpg|webp)",
    r"/upload/[^\"'\s>]+\.(?:png|jpg|webp)",
]
found: set[str] = set()
for pat in patterns:
    found.update(re.findall(pat, html, re.I))
print(f"image urls in page: {len(found)}")
for u in sorted(found)[:15]:
    print(" ", u)

# __NEXT_DATA__ or JSON blobs
for m in re.finditer(r"<script[^>]*id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>", html, re.S):
    try:
        nd = json.loads(m.group(1))
        print("__NEXT_DATA__ keys:", nd.keys())
    except Exception:
        pass

# collectory KR set cards - check all fields
r = httpx.get(
    "https://collectory.cc/api/sets/611cf371-dafe-42fc-b86d-895aa433e10d/cards",
    timeout=60,
)
cards = r.json().get("cards", [])
for c in cards:
    n = int(c["card_number"].split("/")[0])
    if 102 <= n <= 111:
        print(
            f"\n{n:03d} name_ko={c.get('name_ko')} region={c.get('region')}\n"
            f"  image_url={c.get('image_url')}\n"
            f"  cdn_image_url={c.get('cdn_image_url')}"
        )
