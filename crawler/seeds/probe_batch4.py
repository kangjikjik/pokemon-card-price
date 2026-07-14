"""4배치 페이지·박스이미지 탐색"""
from __future__ import annotations

import re
import time

import httpx

from verify_batch1_kr import parse_release_date, scrape_page

PLACEHOLDER = "2016-06-20_00-44-39-61799-1466351079"
IMG_RE = re.compile(
    r"(https://data1\.pokemonkorea\.co\.kr/20\d{2}/[^\"'\s>]+\.(?:png|jpg|PNG|JPG))"
)

PAGE_MAP = {
    "XY8a": 65,
    "XY7": 50,
    "XY6": 47,
    "XY5a": 44,
    "XY5b": 44,
    "XY4": 40,
    "XY3": 36,
    "XY2": 33,
    "EBB1": 0,
    "XY5": 25,
    "XY3a": 9,
    "BW4": 13,
}

# 구간 확장팩 기본 발매가 (pokemoncard 미표기)
DEFAULT_MSRP = {
    "XY8a": (500, 15000),
    "XY7": (500, 15000),
    "XY6": (500, 15000),
    "XY5a": (500, 15000),
    "XY5b": (500, 15000),
    "XY4": (500, 15000),
    "XY3": (500, 15000),
    "XY2": (500, 15000),
    "EBB1": (1000, 30000),
    "XY5": (1000, 30000),
    "XY3a": (1000, 30000),
    "BW4": (1000, 30000),
}


def pick_box(html: str) -> str:
    imgs = [u for u in IMG_RE.findall(html) if PLACEHOLDER not in u and "/card/" not in u.lower()]
    imgs.sort(reverse=True)
    return imgs[0] if imgs else ""


def find_ebb1(client: httpx.Client) -> tuple[int, str, str]:
    for p in range(1, 40):
        r = client.get(f"https://pokemoncard.co.kr/card/{p}", timeout=15)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", r.text)
        if not h3:
            continue
        t = h3[0]
        if "EX" in t and "배틀" in t and "부스트" in t:
            return p, parse_release_date(r.text), t
        time.sleep(0.04)
    return 0, "", ""


def main():
    client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    ebb_p, ebb_d, ebb_t = find_ebb1(client)
    if ebb_p:
        PAGE_MAP["EBB1"] = ebb_p
        print(f"EBB1 page={ebb_p} date={ebb_d} title={ebb_t[:50]}")

    for code, page in PAGE_MAP.items():
        if not page:
            print(f"{code} NO PAGE")
            continue
        res = scrape_page(page)
        r = client.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
        r.encoding = "utf-8"
        box = pick_box(r.text)
        pack, box_p = res.get("pack") or DEFAULT_MSRP[code][0], res.get("box") or DEFAULT_MSRP[code][1]
        print(
            f"{code:5} p{page:3} {res.get('released_at','??'):12} "
            f"{pack:5}/{box_p:6} box={'OK' if box else 'MISS'} {res.get('title','')[:40]}"
        )
        if box:
            print(f"      {box[:90]}")


if __name__ == "__main__":
    main()
