"""신규 featured 15세트(3차) pokemoncard.co.kr 발매가·이미지 검증"""
from __future__ import annotations

import re
import sys

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)

NEW_SETS = [
    ("CEL", "25주년", "1331f663-aaa7-4a73-b371-4193edad37bf", "BS2021015"),
    ("S7F", "퓨전아츠", "d4e370fe-533d-4dfb-aac3-ad8aee5a25ab", "BS2021018"),
    ("S7R", "창공스트림", "34e421b1-6596-4b38-b7c1-f21847d6b5fb", "BS2021012"),
    ("S7D", "마천퍼펙트", "f0c3efc5-e7fb-4c14-bfa5-abbf062101a4", "BS2021011"),
    ("S6H", "이브이 히어로즈", "def98ed9-e26e-46bf-b516-b2496d6991cf", "BS2021007"),
    ("S6G", "칠흑의 가이스트", "9a4e302d-fed9-4ca5-9370-786b72150099", "BS2021005-kr"),
    ("S6L", "백은의 랜스", "b4d866a2-34b8-4a86-9556-a47920afb5e6", "BS2021004"),
    ("S5F", "쌍벽의 파이터", "1ec93be9-c0e7-46c3-9ab9-faa79a180ed3", "BS2021003"),
    ("S5S", "일격마스터", "5f36330a-67b5-468b-b8f1-23a58817705e", "BS2021001"),
    ("S5P", "연격마스터", "00cacf92-f2c6-49e9-a3a6-fc97473aee19", "BS2021002"),
    ("S4SV", "샤이니스타", "05273182-6ced-4135-95ad-57070ce7c8e5", "BS2020016"),
    ("S4B", "볼트태클", "17ebdf5d-3926-4a5b-9782-97e4f2fa15d2", "BS2020014"),
    ("S3H", "전설의 고동", "49f5ab81-05f8-440d-ad0e-95ad18047a95", "BS2020012"),
    ("S3Z", "무한존", "5390bef2-f4cf-47bd-a7db-958413420a88", "BS2020011"),
    ("S2R", "폭염워커", "e269c01e-c490-4cc4-8a2e-477988dfc536", "BS2020010"),
]


def scrape_kr(img_url: str, name: str) -> tuple[int, int, int]:
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    img_key = ""
    if img_url and "pokemonkorea.co.kr" in img_url:
        img_key = img_url.split("/")[-1].replace(".png", "").replace(".jpg", "")
    needles = [name, name.replace(" ", ""), name[:4]]
    for page in range(350, 960):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        hit = (img_key and img_key in r.text) or any(
            n and (n in r.text or n in r.text.replace(" ", "")) for n in needles
        )
        if not hit:
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
    all_sets = httpx.get("https://collectory.cc/api/sets", timeout=60).json().get("sets") or []
    by_id = {s["id"]: s for s in all_sets}

    print(f"{'code':5} | {'date':12} | {'pack':>6} | {'box':>7} | {'page':>4} | {'cards':>4} | name")
    print("-" * 85)
    ok = 0
    for code, name_kr, cid, _bs in NEW_SETS:
        meta = by_id.get(cid, {})
        img = meta.get("image_url") or ""
        page, pack, box = scrape_kr(img, name_kr)
        cards = httpx.get(f"https://collectory.cc/api/sets/{cid}/cards", timeout=90).json().get("cards") or []
        date = meta.get("release_date_ko") or ""
        status = "OK" if page and pack else "FAIL"
        if status == "OK":
            ok += 1
        print(
            f"{code:5} | {date:12} | {pack:6} | {box:7} | {page:4} | {len(cards):4} | "
            f"{meta.get('name_ko') or name_kr} [{status}]"
        )
        if img:
            print(f"       img={img}")


if __name__ == "__main__":
    main()
