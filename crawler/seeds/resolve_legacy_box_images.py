"""구간 pokemoncard 페이지 — pokemonkorea 박스 이미지 매핑"""
from __future__ import annotations

import re

import httpx

from verify_batch1_kr import scrape_page

PAGES = {
    "XY8a": 65,
    "XY7": 50,
    "XY6": 47,
    "XY5a": 44,
    "XY5b": 44,
    "XY4": 40,
    "XY3": 36,
    "XY2": 33,
    "EBB1": 27,
    "XY5": 25,
    "XY3a": 9,
    "BW4": 13,
}

MAIN_IMG = re.compile(
    r"(https?://pokemonkorea\.co\.kr/templates/default/content_image/card/"
    r"(?:[^\"'\s>]*main[^\"'\s>]*\.(?:png|jpg|PNG|JPG)))",
    re.I,
)
DATA1_IMG = re.compile(
    r"(https://data1\.pokemonkorea\.co\.kr/20\d{2}/[^\"'\s>]+\.(?:png|jpg|PNG|JPG))",
)
PLACEHOLDER = "2016-06-20_00-44-39-61799-1466351079"


def pick_box(html: str) -> str:
    data1 = [u for u in DATA1_IMG.findall(html) if PLACEHOLDER not in u]
    if data1:
        data1.sort(reverse=True)
        return data1[0]
    mains = MAIN_IMG.findall(html)
    if mains:
        # card_main_* 우선
        mains.sort(key=lambda u: (0 if "card_main" in u.lower() else 1, u))
        return mains[0]
    return ""


def main():
    c = httpx.Client(timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    for code, page in PAGES.items():
        r = c.get(f"https://pokemoncard.co.kr/card/{page}")
        r.encoding = "utf-8"
        box = pick_box(r.text)
        res = scrape_page(page)
        print(f"{code:5} p{page:3} box={'OK' if box else 'MISS'}")
        if box:
            print(f"      {box}")


if __name__ == "__main__":
    main()
