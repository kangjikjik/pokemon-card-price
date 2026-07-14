"""흰 배경 팩 이미지 → 검정 배경으로 변환 후 public/set-boxes 저장 + kr_sets 동기화"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "set-boxes"
PUBLIC.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

# 세트코드 → 소스 URL (S6H는 올바른 팩으로 교체)
SOURCES: dict[str, str] = {
    # 이브이 히어로즈 — 스페셜세트(SP4) 말고 일반 강화확장팩 (검정 배경)
    "S6H": "https://data1.pokemonkorea.co.kr/2021/07/2021-07-22_11-54-15-63258-1626922455.png",
    # 흰 배경 팩들 — 동일 URL이어도 배경 검정 처리
    "S3H": "https://data1.pokemonkorea.co.kr/2020/09/2020-09-09_11-56-00-27651-1599620160.png",
    "S3Z": "https://data1.pokemonkorea.co.kr/2020/07/2020-07-10_18-14-20-33148-1594372460.png",
    "S2R": "https://data1.pokemonkorea.co.kr/2020/06/2020-06-03_09-51-03-72811-1591145463.png",
    "S2": "https://data1.pokemonkorea.co.kr/2020/04/2020-04-09_15-43-53-72986-1586414633.png",
    "S4B": "https://data1.pokemonkorea.co.kr/2020/10/2020-10-07_18-03-37-36741-1602061417.png",
    "S4SV": "https://data1.pokemonkorea.co.kr/2020/11/2020-11-26_18-20-13-99929-1606382413.png",
    "S1a": "https://data1.pokemonkorea.co.kr/2020/03/2020-03-19_17-16-22-65387-1584605782.png",
}


def whiten_to_black(im: Image.Image, threshold: int = 245) -> Image.Image:
    """거의 흰 배경 픽셀을 검정으로 교체 (코너 flood 기반)"""
    im = im.convert("RGBA")
    pixels = im.load()
    w, h = im.size

    def is_white(x: int, y: int) -> bool:
        r, g, b, a = pixels[x, y]
        return a > 200 and r >= threshold and g >= threshold and b >= threshold

    visited = set()
    stack = []
    # 네 모서리 + 가장자리 샘플에서 시작
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if is_white(x, y):
            stack.append((x, y))
    for x in range(0, w, max(1, w // 40)):
        for y in (0, h - 1):
            if is_white(x, y):
                stack.append((x, y))
    for y in range(0, h, max(1, h // 40)):
        for x in (0, w - 1):
            if is_white(x, y):
                stack.append((x, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        if not (0 <= x < w and 0 <= y < h):
            continue
        if not is_white(x, y):
            continue
        visited.add((x, y))
        pixels[x, y] = (15, 23, 42, 255)  # slate-950-ish
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    return im


def local_name(code: str) -> str:
    return f"{code.replace('+', 'plus')}.png"


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    fixes: dict[str, str] = {}

    for code, url in SOURCES.items():
        print(f"{code}: fetch {url.split('/')[-1]}")
        data = client.get(url).content
        im = Image.open(__import__("io").BytesIO(data))
        out = whiten_to_black(im)
        path = PUBLIC / local_name(code)
        out.save(path, optimize=True)
        rel = f"/set-boxes/{path.name}"
        fixes[code] = rel
        print(f"  -> {path.name} ({path.stat().st_size} bytes)")

    updated = []
    changed = []
    for s in KR_SETS:
        ns = s
        if s.code in fixes and fixes[s.code] != s.box_image_kr:
            changed.append((s.code, s.name_kr, fixes[s.code]))
            ns = replace(s, box_image_kr=fixes[s.code])
        if ns.box_image_kr:
            sb.table("card_sets").update({"image_url": ns.box_image_kr}).eq("set_code", s.code).execute()
        updated.append(ns)

    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images(updated)
    print(f"\nchanged {len(changed)}")
    for code, name, url in changed:
        print(f"  {code} {name} -> {url}")


if __name__ == "__main__":
    main()
