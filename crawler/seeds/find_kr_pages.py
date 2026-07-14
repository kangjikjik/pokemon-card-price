"""pokemoncard.co.kr에서 세트명으로 제품 페이지·발매가 검색"""
from __future__ import annotations

import re
import sys

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg))")

QUERIES = [
    ("SV4K", "고대의 포효"),
    ("SV4M", "미래의 일섬"),
    ("SV3a", "레이징서프"),
    ("SV3", "흑염의 지배자"),
    ("SV2a", "포켓몬 카드 151"),
    ("SV2D", "클레이버스트"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    for code, needle in QUERIES:
        found = False
        for page in range(550, 960):
            r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
            if r.status_code != 200:
                continue
            r.encoding = "utf-8"
            if needle not in r.text and needle.replace(" ", "") not in r.text:
                continue
            m = KR_PRICE_RE.search(r.text)
            imgs = IMG_RE.findall(r.text)
            box_imgs = [u for u in imgs if "pokemonkorea" in u]
            print(f"\n{code} page={page} needle={needle}")
            if m:
                print(f"  pack={m.group(1)} box={m.group(2)}")
            for u in box_imgs[:3]:
                print(f"  img={u}")
            found = True
            break
        if not found:
            print(f"\n{code} NOT FOUND for {needle}")


if __name__ == "__main__":
    main()
