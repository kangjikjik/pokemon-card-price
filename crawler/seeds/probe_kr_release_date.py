"""pokemoncard.co.kr 제품 페이지 — 발매일·발매가·박스이미지 추출"""
from __future__ import annotations

import re
import sys

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg|PNG|JPG))")
# 발매일: 2025년 7월 25일 / 2025.07.25 / 2025-07-25
DATE_RE = re.compile(
    r"(?:발매일|출시일|발매)\s*[:\s]*"
    r"(20\d{2})\s*년?\s*(\d{1,2})\s*월?\s*(\d{1,2})\s*일?"
    r"|(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})",
    re.I,
)

SETS = [
    ("MG1b", 785, "로켓단의 영광"),
    ("MG2a", 796, "화이트플레어"),
    ("MG4a", 859, "MEGA 드림"),
]


def parse_date(text: str) -> str:
    for m in DATE_RE.finditer(text):
        g = m.groups()
        if g[0]:
            y, mo, d = g[0], g[1], g[2]
        else:
            y, mo, d = g[3], g[4], g[5]
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return ""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    for code, page, name in SETS:
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        r.encoding = "utf-8"
        m = KR_PRICE_RE.search(r.text)
        imgs = IMG_RE.findall(r.text)
        box = imgs[0] if imgs else ""
        date = parse_date(r.text)
        h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", r.text)
        print(f"\n{code} page={page} ({name})")
        print(f"  h3: {h3[0] if h3 else '?'}")
        print(f"  date: {date or 'NOT FOUND'}")
        print(f"  price: {m.groups() if m else 'NOT FOUND'}")
        print(f"  box: {box[:95] if box else 'NOT FOUND'}")


if __name__ == "__main__":
    main()
