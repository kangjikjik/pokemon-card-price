"""2배치 — 알려진 페이지에서 발매일·가격·이미지 재검증 (제목 확인)"""
from __future__ import annotations

import json
import re
import sys
import time

import httpx

from scrape_batch2 import BATCH2_SETS, pick_box_from_html
from verify_batch1_kr import parse_release_date, scrape_page

HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT = __file__.replace("verify_batch2_pages.py", "batch2_scraped.json")

# scrape_gaps_log.txt 힌트 (제목으로 재검증)
PAGE_HINTS: dict[str, int] = {
    "S2": 297,
    "S1a": 291,
    "S1W": 80,
    "S1H": 152,
    "SM12a": 163,
    "SM12": 261,
    "SM11b": 257,
    "SM11a": 211,
    "SM10": 180,
    "SM9": 166,
    "SM8b": 163,
    "SM9a": 156,
    "SM8": 152,
    "SM7": 149,
    "SM7a": 120,
}

KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)


def title_matches(name_kr: str, title: str) -> bool:
    t = title.replace(" ", "")
    n = name_kr.replace(" ", "")
    if n in t or n[:4] in t:
        return True
    if "TAG" in name_kr and "태그올스타" in title:
        return True
    if "VMAX" in name_kr and "VMAX" in title:
        return True
    if "REMASTER" in name_kr and "REMASTER" in title.upper():
        return True
    if name_kr == "소드" and "소드" in title:
        return True
    if name_kr == "실드" and "실드" in title:
        return True
    return False


def find_nearby(client: httpx.Client, code: str, name: str, hint: int) -> dict | None:
    for page in [hint] + [hint + d for d in (-2, -1, 1, 2, 3, -3, 4, 5)]:
        if page < 50:
            continue
        res = scrape_page(page)
        time.sleep(0.12)
        if res.get("status") != "OK":
            continue
        if title_matches(name, res.get("title", "")):
            return res
    # 넓은 범위
    for page in range(max(50, hint - 20), hint + 30):
        if page == hint:
            continue
        res = scrape_page(page)
        time.sleep(0.08)
        if res.get("status") != "OK":
            continue
        if title_matches(name, res.get("title", "")):
            return res
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(timeout=20, headers=HEADERS)
    rows = []

    print(f"{'code':6} | {'page':>4} | {'date':12} | {'pack':>6} | {'box':>7} | title")
    print("-" * 95)

    for code, name_kr, cid, bs in BATCH2_SETS:
        hint = PAGE_HINTS.get(code, 0)
        res = find_nearby(client, code, name_kr, hint) if hint else None

        if not res:
            print(f"{code:6} | FAIL | {name_kr}")
            rows.append({"code": code, "status": "FAIL", "collectory_id": cid, "bs_code": bs, "name_kr": name_kr})
            continue

        page = res["page"]
        r = client.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
        r.encoding = "utf-8"
        box_img = pick_box_from_html(r.text)

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
            "status": "OK",
        }
        rows.append(row)
        print(
            f"{code:6} | {page:4} | {row['released_at']:12} | "
            f"{row['msrp_pack_kr']:6} | {row['msrp_box_kr']:7} | {row['title'][:45]}"
        )

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in rows if r.get("status") == "OK")
    print(f"\nOK={ok}/{len(BATCH2_SETS)}")


if __name__ == "__main__":
    main()
