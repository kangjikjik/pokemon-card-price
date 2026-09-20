"""포켓몬코리아 MG6 카드 이미지 URL 패턴 탐색."""
from __future__ import annotations

import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0"}

# pokemoncard 카드 검색/목록 페이지 후보
pages = [
    "https://pokemoncard.co.kr/product/view/907",
    "https://pokemoncard.co.kr/product/907",
    "https://pokemoncard.co.kr/card/search?keyword=BS2026004",
    "https://pokemoncard.co.kr/card/search?keyword=아이언디펜더",
    "https://pokemoncard.co.kr/card/search?keyword=어비스아이",
]
for url in pages:
    try:
        r = httpx.get(url, headers=H, timeout=20, follow_redirects=True)
        print(f"{r.status_code} {url} -> final {r.url} len={len(r.text)}")
        imgs = set(re.findall(r"https://data1\.pokemonkorea\.co\.kr/[^\s\"'<>]+", r.text))
        if imgs:
            for u in sorted(imgs)[:5]:
                print(" ", u)
    except Exception as e:
        print(f"ERR {url} {e}")

# data1.pokemonkorea URL 패턴 brute
candidates = []
for fmt in [
    "https://data1.pokemonkorea.co.kr/MEGA/M5/{n:03d}.png",
    "https://data1.pokemonkorea.co.kr/MEGA/M5/{n:03d}.webp",
    "https://data1.pokemonkorea.co.kr/MEGA/M5/{n}_081.png",
    "https://data1.pokemonkorea.co.kr/MEGA/M5/card_{n:03d}.png",
    "https://data1.pokemonkorea.co.kr/card/BS2026004/{n:03d}.png",
    "https://data1.pokemonkorea.co.kr/card/BS2026004/{n}_081.png",
]:
    for n in [102, 103, 105]:
        candidates.append(fmt.format(n=n))

print("\nHEAD probe:")
for url in candidates:
    r = httpx.head(url, timeout=10, follow_redirects=True)
    if r.status_code == 200:
        print("OK", url, r.headers.get("content-type"), r.headers.get("content-length"))
