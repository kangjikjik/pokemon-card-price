"""박스 이미지 품질 수정 — 배너/중복 제거, kr_sets·DB·web 동기화"""
from __future__ import annotations

import os
import re
import struct
import sys
import time
from dataclasses import replace

import httpx
from dotenv import load_dotenv
from supabase import create_client

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from kr_sets import KR_SETS, KrSet
from resolve_legacy_box_images import DATA1_IMG, MAIN_IMG, PLACEHOLDER
from revert_featured_55 import write_set_images

# 동일 페이지·수동 분리 필요
MANUAL: dict[str, str] = {
    "S2": "https://data1.pokemonkorea.co.kr/2020/04/2020-04-09_15-43-53-72986-1586414633.png",
    "S1W": "https://data1.pokemonkorea.co.kr/2020/01/2020-01-21_18-35-45-24231-1579599345.png",
    "S1H": "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png",
    "SM12a": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-27_14-58-02-27796-1574834282.png",
    "SM12": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-27_15-03-02-87345-1574834582.png",
    "SM10": "https://data1.pokemonkorea.co.kr/2019/05/2019-05-02_11-39-44-89132-1556764784.jpg",
    "SM9a": "https://data1.pokemonkorea.co.kr/2019/01/2019-01-10_10-13-46-90179-1547082826.png",
    "SM6a": "https://data1.pokemonkorea.co.kr/2018/06/2018-06-22_18-47-50-16043-1529660870.png",
    "SM5+": "https://data1.pokemonkorea.co.kr/2018/03/2018-03-27_14-42-19-96152-1522129339.PNG",
    "SM4+": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-09_19-29-12-23396-1515493752.jpg",
    "SM4": "https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png",
    "SM4a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "SM7a": "https://data1.pokemonkorea.co.kr/2017/12/2017-12-08_17-21-07-46128-1512721267.jpg",
    "CP6": "https://data1.pokemonkorea.co.kr/2016/09/2016-09-20_13-45-22-59022-1474346722.jpg",
    "XY8a": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY10_main_OuZo_4.jpg",
    "SM2+": "https://data1.pokemonkorea.co.kr/2017/10/2017-10-24_18-33-58-94770-1508837638.png",
    "SM1M": "https://data1.pokemonkorea.co.kr/2017/01/2017-01-30_14-43-58-88992-1485755038.png",
    "SM1C": "https://data1.pokemonkorea.co.kr/2017/02/2017-02-06_10-53-10-20216-1486345990.png",
}

BAD_FRAG = re.compile(r"hover|banner|bg_|gms\d", re.I)
_DIM_CACHE: dict[str, tuple[int, int]] = {}


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    return None


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    i = 2
    while i < len(data):
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 3 : i + 7])
            return w, h
        if i + 1 >= len(data):
            break
        seg = struct.unpack(">H", data[i : i + 2])[0]
        i += seg
    return None


def image_dims(client: httpx.Client, url: str) -> tuple[int, int]:
    if url in _DIM_CACHE:
        return _DIM_CACHE[url]
    try:
        r = client.get(url)
        sz = _png_size(r.content[:65536]) or _jpeg_size(r.content[:65536])
        if sz:
            _DIM_CACHE[url] = sz
            return sz
    except Exception:
        pass
    return 0, 0


def score_box_url(client: httpx.Client, url: str) -> int:
    if not url or PLACEHOLDER in url:
        return -100
    if BAD_FRAG.search(url):
        return -50
    w, h = image_dims(client, url)
    if not w:
        return 0
    ratio = w / h
    s = 0
    if ratio > 1.3:
        s -= 25
    elif ratio < 0.9:
        s += 10
    else:
        s += 18
    if 280 <= w <= 700 and 250 <= h <= 700:
        s += 5
    if url.lower().endswith(".png"):
        s += 3
    if "main" in url.lower():
        s += 5
    return s


def pick_box_from_page(client: httpx.Client, html: str, code: str) -> str:
    if code in MANUAL:
        return MANUAL[code]
    candidates: list[str] = []
    for u in DATA1_IMG.findall(html):
        if PLACEHOLDER not in u and "/card/" not in u.lower():
            candidates.append(u)
    candidates.extend(MAIN_IMG.findall(html))
    seen: set[str] = set()
    uniq = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    if not uniq:
        return ""
    uniq.sort(key=lambda u: score_box_url(client, u), reverse=True)
    best = uniq[0]
    return best if score_box_url(client, best) > 0 else ""


def needs_fix(client: httpx.Client, url: str) -> bool:
    if not url:
        return True
    if PLACEHOLDER in url or BAD_FRAG.search(url):
        return True
    w, h = image_dims(client, url)
    if w and h and w / h > 1.3:
        return True
    return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})

    updated: list[KrSet] = []
    fixes: list[tuple[str, str, str]] = []

    for s in KR_SETS:
        ns = s
        new_box = ""

        if s.code in MANUAL:
            new_box = MANUAL[s.code]
        elif s.pokemoncard_page:
            r = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}", timeout=15)
            r.encoding = "utf-8"
            if needs_fix(client, s.box_image_kr or ""):
                new_box = pick_box_from_page(client, r.text, s.code)
            time.sleep(0.04)

        if new_box and new_box != s.box_image_kr:
            if score_box_url(client, new_box) >= score_box_url(client, s.box_image_kr or ""):
                fixes.append((s.code, s.box_image_kr or "", new_box))
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
            print(f"  {code}: {old.split('/')[-1]} -> {new.split('/')[-1]}")
    else:
        print("no fixes needed")


if __name__ == "__main__":
    main()
