"""신규 10세트 pokemoncard.co.kr 발매가·이미지 검증"""
from __future__ import annotations

import re
import sys

import httpx

from collectory_map import COLLECTORY_API

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)

NEW_SETS = [
    ("SV5M", "크림슨헤이즈", "6e1478e0-1136-4891-b306-9fd15af573b3", "BS2024007"),
    ("SV4x", "사이버저지", "41ef4da6-36d9-473f-8098-d09a6f4f1a18", "BS2024005"),
    ("SV4", "와일드포스", "4cfdf0c9-3712-450a-9b94-dfec8bdf03ef", "BS2024004"),
    ("SV4a", "샤이니 트레저 ex", "43856548-fd3a-4ef2-bf29-56a7f1f2ca47", "BS2024001"),
    ("SV4K", "고대의 포효", "30f2f093-166a-4a52-98f7-54986d22716a", "BS2023021"),
    ("SV4M", "미래의 일섬", "c4588968-e2f7-4e00-89ea-738e078ab28c", "BS2023022"),
    ("SV3a", "레이징서프", "486d2edc-97ef-4dcc-a228-f3eac8047f7f", "BS2023020"),
    ("SV3", "흑염의 지배자", "75e1549c-efd4-470a-bb12-2340868e450e", "BS2023015"),
    ("SV2a", "포켓몬 카드 151", "1d7e469a-95d9-4710-a9c3-09ad381b40cc", "BS2023014"),
    ("SV2D", "클레이버스트", "c5727254-a617-495d-ac80-d58c76280bef", "BS2023012"),
]

JP_URLS = {
    "SV5M": "https://www.pokemon-card.com/ex/sv5/",
    "SV4x": "https://www.pokemon-card.com/ex/sv4/",
    "SV4": "https://www.pokemon-card.com/ex/sv4/",
    "SV4a": "https://www.pokemon-card.com/ex/sv4a/",
    "SV4K": "https://www.pokemon-card.com/ex/sv4/",
    "SV4M": "https://www.pokemon-card.com/ex/sv4/",
    "SV3a": "https://www.pokemon-card.com/products/sv/sv3a.html",
    "SV3": "https://www.pokemon-card.com/ex/sv3/",
    "SV2a": "https://www.pokemon-card.com/ex/sv2a/",
    "SV2D": "https://www.pokemon-card.com/ex/sv2/",
}


def scrape_kr(img_url: str) -> tuple[int, int, int]:
    if "pokemonkorea.co.kr" not in img_url:
        return 0, 0, 0
    img_key = img_url.split("/")[-1].replace(".png", "").replace(".jpg", "")
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    for page in range(600, 960):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        if img_key not in r.text:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        return (
            page,
            int(m.group(1).replace(",", "")),
            int(m.group(2).replace(",", "")),
        )
    return 0, 0, 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    all_sets = httpx.get(f"{COLLECTORY_API}/sets", timeout=60).json().get("sets") or []
    by_id = {s["id"]: s for s in all_sets}

    print(f"{'code':5} | {'date':12} | {'pack':>6} | {'box':>7} | {'page':>4} | {'cards':>4} | name")
    print("-" * 75)
    for code, name_kr, cid, bs in NEW_SETS:
        meta = by_id.get(cid, {})
        img = meta.get("image_url") or ""
        page, pack, box = scrape_kr(img)
        cards = httpx.get(f"{COLLECTORY_API}/sets/{cid}/cards", timeout=90).json().get("cards") or []
        date = meta.get("release_date_ko") or ""
        print(f"{code:5} | {date:12} | {pack:6} | {box:7} | {page:4} | {len(cards):4} | {meta.get('name_ko') or name_kr}")
        if img:
            print(f"       img={img}")


if __name__ == "__main__":
    main()
