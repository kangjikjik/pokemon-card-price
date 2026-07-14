"""2배치 15팩 — pokemoncard.co.kr 발매일·가격·박스이미지 검증"""
from __future__ import annotations

import json
import re
import sys
import time

import httpx

from verify_batch1_kr import find_page_by_needle, parse_release_date, scrape_page

HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT = __file__.replace("scrape_batch2.py", "batch2_scraped.json")

# pick_batch2.py 선정 (S2R 직전 구간, collectory 발매일 최신순 15)
BATCH2_SETS = [
    ("S2", "반역크래시", "f2764878-6073-4691-8252-36a5feda61a6", "BS2020005-kr"),
    ("S1a", "VMAX라이징", "68d9fa83-0786-4141-8e47-8eb2c4f31e99", "BS2020004-kr"),
    ("S1W", "소드", "17de57f7-83ed-44ef-8a8c-c532407ab394", "BS2020002"),
    ("S1H", "실드", "5ddc68ce-514c-490b-846e-3c9dfca1bfd4", "BS2020003"),
    ("SM12a", "TAG TEAM GX 태그올스타즈", "885b7cb1-7a47-4718-a8dd-eb2f929e881b", "BS2019017"),
    ("SM12", "얼터제네시스", "4391a84d-4cf6-494e-aaed-b32e4e78a60b", "BS2019016-kr"),
    ("SM11b", "드림리그", "28af28cd-edcb-4234-8291-aabb5bc11593", "BS2019015"),
    ("SM11a", "미라클트윈", "8b6beb3d-422f-47a1-bf3d-d27f0ebbc489", "BS2019013-kr"),
    ("SM10", "더블블레이즈", "4702f8bc-f4c6-4a18-8c3d-ab60b1fb893d", "BS2019007-kr"),
    ("SM9", "나이트유니슨", "e73363cb-6e58-464b-b5e4-1eed097866cf", "BS2019003-kr"),
    ("SM8b", "GX 울트라샤이니", "1758a1f2-dca4-4956-8e8e-49468c486163", "BS2019002"),
    ("SM9a", "태그볼트", "ee356460-f869-4d0a-a611-b506b15c7048", "BS2019001-kr"),
    ("SM8", "플라스마 스파크", "d9a8e5c0-8fe5-4651-9d2a-f88fcd92fb90", "BS2018012-kr"),
    ("SM7", "버스트임팩트", "cea23066-004d-4e9b-bb85-81ffe66cd644", "BS2018010-kr"),
    ("SM7a", "GX 배틀부스트 REMASTER", "662e9195-2eaa-480b-9286-35ae9e7f69b5", "BS2018011-kr"),
]

IMG_RE = re.compile(
    r"(https://data1\.pokemonkorea\.co\.kr/20\d{2}/[^\"'\s>]+\.(?:png|jpg|PNG|JPG))"
)


def pick_box_from_html(html: str) -> str:
    imgs = IMG_RE.findall(html)
    # 카드 이미지 제외, 최신 연도 우선
    boxes = [u for u in imgs if "/card/" not in u.lower()]
    if not boxes:
        boxes = imgs
    boxes.sort(reverse=True)
    return boxes[0] if boxes else ""


def search_name_variants(name: str) -> list[str]:
    variants = [name, name.replace(" ", "")]
    # 축약 검색
    if "TAG TEAM" in name:
        variants.append("태그올스타")
    if "VMAX" in name:
        variants.append("VMAX라이징")
    if "REMASTER" in name:
        variants.append("배틀부스트")
    if len(name) > 6:
        variants.append(name[:6])
    return variants


def find_page(code: str, name: str, img_url: str) -> dict:
    for needle in search_name_variants(name):
        res = find_page_by_needle(needle, img_url, page_min=250, page_max=400)
        if res:
            return res
        time.sleep(0.1)
    return find_page_by_needle(name, img_url, page_min=250, page_max=960)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(timeout=60, headers=HEADERS)
    all_sets = client.get("https://collectory.cc/api/sets").json().get("sets") or []
    by_id = {s["id"]: s for s in all_sets}

    rows = []
    print(f"{'code':6} | {'page':>4} | {'date':12} | {'pack':>6} | {'box':>7} | status")
    print("-" * 80)

    for code, name_kr, cid, bs in BATCH2_SETS:
        meta = by_id.get(cid, {})
        img = meta.get("image_url") or ""
        res = find_page(code, name_kr, img)
        time.sleep(0.2)

        if not res:
            print(f"{code:6} | FAIL | {name_kr}")
            rows.append({"code": code, "name_kr": name_kr, "status": "FAIL", "bs_code": bs, "collectory_id": cid})
            continue

        page = res["page"]
        # 페이지 HTML에서 박스 이미지 재추출
        r = client.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
        r.encoding = "utf-8"
        box_img = pick_box_from_html(r.text) or res.get("box_image_kr") or ""

        row = {
            "code": code,
            "name_kr": name_kr,
            "released_at": res.get("released_at") or parse_release_date(r.text),
            "box_image_kr": box_img,
            "bs_code": bs,
            "collectory_id": cid,
            "msrp_pack_kr": res.get("pack", 0),
            "msrp_box_kr": res.get("box", 0),
            "pokemoncard_page": page,
            "title": res.get("title", ""),
            "collectory_date": meta.get("release_date_ko") or "",
            "status": "OK" if res.get("released_at") and res.get("pack") else "PARTIAL",
        }
        rows.append(row)
        flag = row["status"]
        print(
            f"{code:6} | {page:4} | {row['released_at'] or '??':12} | "
            f"{row['msrp_pack_kr']:6} | {row['msrp_box_kr']:7} | {flag}"
        )
        if row["collectory_date"] and row["released_at"] != row["collectory_date"]:
            print(f"       collectory {row['collectory_date']} != official {row['released_at']}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in rows if r.get("status") == "OK")
    print(f"\nOK={ok}/{len(BATCH2_SETS)} -> {OUT}")


if __name__ == "__main__":
    main()
