"""신규 featured 15세트 pokemoncard.co.kr 발매가·이미지 검증"""
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
    ("SV2P", "스노해저드", "86241e84-73af-4c01-88e8-6d4f642473e2", "BS2023011"),
    ("SV1a", "트리플렛비트", "c4bd1ec1-4c8d-473f-893a-3a2e47d51b24", "BS2023010"),
    ("SV1V", "바이올렛 ex", "323520fd-b42a-426a-8755-efb6f4ffba6d", "BS2023007"),
    ("SV1S", "스칼렛 ex", "84db79c4-277d-4011-bab5-9a04e16b9682", "BS2023006"),
    ("S12a", "VSTAR 유니버스", "e3b441d6-9f5b-4850-8ce9-63628473dd72", "BS2023001"),
    ("S12", "패러다임트리거", "a03b2497-8f0f-40f9-a04c-e0e2eef397c6", "BS2022017"),
    ("S11a", "백열의 아르카나", "9ec2d6c0-4655-4b0b-97b5-5d6173a891a7", "BS2022016"),
    ("S11", "로스트어비스", "0e7c338d-f57b-4192-9eb8-0ad39310ed14", "BS2022014"),
    ("S10b", "다크판타스마", "88ac53de-70d1-4c3b-aac1-b01b9524dd49", "BS2022011-kr"),
    ("S10a", "Pokémon GO", "9e7a8cb5-19bb-4dec-8c49-ccb7b0a6fad0", "BS2022010"),
    ("S9a", "타임게이저", "f6d152c2-29c1-49ec-91ff-ce94750558e8", "BS2022007-kr"),
    ("S9", "스페이스 저글러", "30f1b581-7ab2-4199-af6d-a763747fa4e3", "BS2022008"),
    ("S8", "배틀리전", "eec8bb3b-a3ee-41be-a896-a69bbed3aab6", "BS2022004"),
    ("S8a", "스타버스", "ce9b9cd2-c674-41fc-9019-3f04334629e9", "BS2022002"),
    ("S8b", "VMAX 클라이맥스", "51f13a13-04ab-4b9b-a277-c12887a9a453", "BS2022001"),
]


def scrape_kr(img_url: str, name: str) -> tuple[int, int, int, str]:
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    img_key = ""
    if img_url and "pokemonkorea.co.kr" in img_url:
        img_key = img_url.split("/")[-1].replace(".png", "").replace(".jpg", "")
    for page in range(400, 960):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        hit = False
        if img_key and img_key in r.text:
            hit = True
        elif name.replace(" ", "") in r.text.replace(" ", ""):
            hit = True
        elif name[:4] in r.text:
            hit = True
        if not hit:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        return (
            page,
            int(m.group(1).replace(",", "")),
            int(m.group(2).replace(",", "")),
            img_url or "",
        )
    return 0, 0, 0, img_url or ""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    all_sets = httpx.get(f"{COLLECTORY_API}/sets", timeout=60).json().get("sets") or []
    by_id = {s["id"]: s for s in all_sets}

    print(f"{'code':5} | {'date':12} | {'pack':>6} | {'box':>7} | {'page':>4} | {'cards':>4} | name")
    print("-" * 85)
    ok = 0
    for code, name_kr, cid, bs in NEW_SETS:
        meta = by_id.get(cid, {})
        img = meta.get("image_url") or ""
        page, pack, box, img_out = scrape_kr(img, name_kr)
        cards = httpx.get(f"{COLLECTORY_API}/sets/{cid}/cards", timeout=90).json().get("cards") or []
        date = meta.get("release_date_ko") or ""
        status = "OK" if page and pack else "FAIL"
        if status == "OK":
            ok += 1
        print(
            f"{code:5} | {date:12} | {pack:6} | {box:7} | {page:4} | {len(cards):4} | "
            f"{meta.get('name_ko') or name_kr} [{status}]"
        )
        if img_out:
            print(f"       img={img_out}")
    print(f"\nverified: {ok}/{len(NEW_SETS)}")


if __name__ == "__main__":
    main()
