"""개선된 박스 이미지 선택 + 전체 동기화"""
from __future__ import annotations

import re
import time
from dataclasses import replace

import httpx

from kr_sets import KR_SETS, KrSet

PLACEHOLDER = "2016-06-20_00-44-39-61799-1466351079"
DATA1_IMG = re.compile(
    r"(https://data1\.pokemonkorea\.co\.kr/20\d{2}/[^\"'\s>]+\.(?:png|jpg|PNG|JPG|jpeg))"
)
MAIN_IMG = re.compile(
    r"(https?://pokemonkorea\.co\.kr/templates/default/content_image/card/"
    r"(?:[^\"'\s>]*main[^\"'\s>]*\.(?:png|jpg|PNG|JPG)))",
    re.I,
)
BAD_FRAG = re.compile(
    r"hover|banner|bg_|collection.?list|card_info|_bg|gms\d|wide|1920",
    re.I,
)
GOOD_FRAG = re.compile(r"main|pack|box|product|_hover\.png", re.I)

# 수동 보정 — pokemoncard 페이지 자동선택 실패 시
MANUAL: dict[str, str] = {
    "SM5+": "https://data1.pokemonkorea.co.kr/2018/04/2018-04-05_09-55-38-63937-1522889738.png",
    "SM4+": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-09_19-29-12-23396-1515493752.jpg",
    "SM4": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png",
    "SM4a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "SM7a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-27_09-35-24-10929-1511742924.jpg",
    "SM12": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-14_16-56-08-88742-1557464168.png",
    "SM2+": "https://data1.pokemonkorea.co.kr/2017/10/2017-10-24_18-33-58-94770-1508837638.png",
}


def score_url(url: str) -> int:
    u = url.lower()
    if PLACEHOLDER in u:
        return -100
    if BAD_FRAG.search(u):
        return -50
    s = 0
    if u.endswith(".png"):
        s += 10
    if GOOD_FRAG.search(u):
        s += 5
    if "data1.pokemonkorea" in u:
        s += 3
    if "templates" in u and "card_main" in u:
        s += 8
    return s


def pick_best_box(html: str, code: str = "") -> str:
    if code in MANUAL:
        return MANUAL[code]
    candidates: list[str] = []
    for u in DATA1_IMG.findall(html):
        if PLACEHOLDER not in u and "/card/" not in u.lower():
            candidates.append(u)
    candidates.extend(MAIN_IMG.findall(html))
  # dedupe preserve order
    seen: set[str] = set()
    uniq = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    if not uniq:
        return ""
    uniq.sort(key=lambda u: score_url(u), reverse=True)
    return uniq[0]


def fetch_collectory_box(collectory_id: str) -> str:
    if not collectory_id:
        return ""
    r = httpx.get("https://collectory.cc/api/sets", timeout=60)
    for s in r.json().get("sets") or []:
        if s.get("id") == collectory_id and s.get("image_url"):
            url = s["image_url"]
            if "pokemonkorea" in url and score_url(url) > 0:
                return url
    return ""


def resolve_box(s: KrSet, client: httpx.Client) -> str:
    if s.code in MANUAL:
        return MANUAL[s.code]
    col = fetch_collectory_box(s.collectory_id)
    if col and score_url(col) >= 5:
        return col
    if not s.pokemoncard_page:
        return s.box_image_kr or ""
    r = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}", timeout=15)
    r.encoding = "utf-8"
    picked = pick_best_box(r.text, s.code)
    if picked and score_url(picked) > score_url(s.box_image_kr or ""):
        return picked
    return s.box_image_kr or picked or col


def main():
    import os
    import sys
    from dotenv import load_dotenv
    from supabase import create_client

    from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
    from revert_featured_55 import write_set_images

    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})

    updated: list[KrSet] = []
    fixes = []
    for s in KR_SETS:
        new_box = resolve_box(s, client)
        time.sleep(0.05)
        old_score = score_url(s.box_image_kr or "")
        new_score = score_url(new_box or "")
        ns = s
        if new_box and new_box != s.box_image_kr and new_score >= old_score:
            if new_box != s.box_image_kr:
                fixes.append((s.code, s.box_image_kr, new_box))
                ns = replace(s, box_image_kr=new_box)
        if ns.box_image_kr:
            sb.table("card_sets").update({"image_url": ns.box_image_kr}).eq("set_code", s.code).execute()
        updated.append(ns)

    if fixes:
        write_kr_sets(updated)
        ensure_kr_sets_footer()
        write_set_images(updated)
        print(f"fixed {len(fixes)} sets")
        for code, old, new in fixes:
            print(f"  {code}")
            print(f"    - {old.split('/')[-1] if old else 'empty'}")
            print(f"    + {new.split('/')[-1]}")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
