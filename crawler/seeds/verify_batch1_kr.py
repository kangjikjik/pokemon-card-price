"""pokemoncard.co.kr — 발매일·발매가·박스이미지 검증 (한 세트/페이지)"""
from __future__ import annotations

import re
import sys

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(
    r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg|PNG|JPG|jpeg))"
)
# 본문·메타에서 한국 발매일
DATE_PATTERNS = [
    re.compile(r"발매일\s*</[^>]+>\s*[^<]*?(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", re.I),
    re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*발매", re.I),
    re.compile(r"발매\s*(?:일|일자)?\s*[:：]?\s*(20\d{2})\.(\d{1,2})\.(\d{1,2})", re.I),
    re.compile(r"(20\d{2})-(\d{2})-(\d{2})"),
]


def parse_release_date(html: str) -> str:
    # 공식: <li><b>발매일</b> 2025-06-20 </li>
    m = re.search(r"<li>\s*<b>발매일</b>\s*(20\d{2}-\d{2}-\d{2})", html, re.I)
    if m:
        return m.group(1)
    for pat in DATE_PATTERNS:
        m = pat.search(html)
        if m:
            y, mo, d = m.group(1), m.group(2), m.group(3)
            return f"{y}-{int(mo):02d}-{int(d):02d}"
    return ""


def pick_box_image(html: str) -> str:
    imgs = IMG_RE.findall(html)
    # 제품 메인 박스 — 보통 첫 pokemonkorea 이미지
    for u in imgs:
        if "pokemonkorea" in u and "card/" not in u.lower():
            return u
    return imgs[0] if imgs else ""


def scrape_page(page: int) -> dict:
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
    r.encoding = "utf-8"
    if r.status_code != 200:
        return {"page": page, "status": "HTTP_FAIL"}
    m = KR_PRICE_RE.search(r.text)
    title_m = re.search(r"<h3[^>]*>([^<]+)</h3>", r.text)
    return {
        "page": page,
        "status": "OK" if m else "NO_PRICE",
        "title": (title_m.group(1) if title_m else "").strip(),
        "released_at": parse_release_date(r.text),
        "pack": int(m.group(1).replace(",", "")) if m else 0,
        "box": int(m.group(2).replace(",", "")) if m else 0,
        "box_image_kr": pick_box_image(r.text),
    }


def find_page_by_needle(
    name_kr: str,
    img_url: str = "",
    title_must: str = "",
    page_min: int = 300,
    page_max: int = 960,
) -> dict | None:
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    img_key = ""
    if img_url and "pokemonkorea" in img_url:
        img_key = img_url.rsplit("/", 1)[-1].split(".")[0][:20]
    needles = [name_kr, name_kr.replace(" ", ""), name_kr[:6], name_kr[:4]]
    for page in range(page_min, page_max):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        hit = (img_key and img_key in r.text) or any(
            n and len(n) >= 2 and (n in r.text or n in r.text.replace(" ", ""))
            for n in needles
        )
        if not hit:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        title_m = re.search(r"<h3[^>]*>([^<]+)</h3>", r.text)
        title = (title_m.group(1) if title_m else "").strip()
        if title_must and title_must not in title:
            continue
        return {
            "page": page,
            "status": "OK",
            "title": title,
            "released_at": parse_release_date(r.text),
            "pack": int(m.group(1).replace(",", "")),
            "box": int(m.group(2).replace(",", "")),
            "box_image_kr": pick_box_image(r.text),
        }
    return None


BATCH1 = [
    ("MG1b", "로켓단의 영광", "40147c73-4a1e-412c-aa48-ee697f9c3e14", "BS2025006",
     "https://data1.pokemonkorea.co.kr/2025/05/2025-05-28_17-24-50-69720-1748420690.png"),
    ("MG2a", "화이트플레어", "7dfcee5a-5e1a-4886-9694-44020932b47b", "BS2025008",
     "https://data1.pokemonkorea.co.kr/2025/07/2025-07-10_16-51-40-50682-1752133900.png"),
    ("MG4a", "MEGA 드림 ex", "ede55e39-375f-43ba-b325-5a8d3d46cd29", "BS2025015",
     "https://cdn.collectory.cc/sets/ede55e39-375f-43ba-b325-5a8d3d46cd29.png"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{'code':6} | {'page':>4} | {'date':12} | {'pack':>6} | {'box':>7} | title")
    print("-" * 90)
    for code, name, _cid, _bs, img in BATCH1:
        res = find_page_by_needle(name, img)
        if not res:
            print(f"{code:6} | FAIL | {name}")
            continue
        print(
            f"{code:6} | {res['page']:4} | {res.get('released_at') or '??':12} | "
            f"{res['pack']:6} | {res['box']:7} | {res.get('title','')[:40]}"
        )
        if res.get("box_image_kr"):
            print(f"       img={res['box_image_kr'][:95]}")


if __name__ == "__main__":
    main()
