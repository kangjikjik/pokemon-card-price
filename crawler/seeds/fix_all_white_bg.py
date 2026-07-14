"""흰 배경 팩 전수 → 검정 배경 변환 + kr_sets/DB/web 동기화"""
from __future__ import annotations

import io
import json
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
OUT = Path(__file__).parent / "_audit_out"
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def whiten_to_black(im: Image.Image, threshold: int = 232) -> Image.Image:
    im = im.convert("RGBA")
    pixels = im.load()
    w, h = im.size

    def is_white(x: int, y: int) -> bool:
        r, g, b, a = pixels[x, y]
        return a > 180 and r >= threshold and g >= threshold and b >= threshold

    visited: set[tuple[int, int]] = set()
    stack: list[tuple[int, int]] = []
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if is_white(x, y):
            stack.append((x, y))
    step_x = max(1, w // 50)
    step_y = max(1, h // 50)
    for x in range(0, w, step_x):
        for y in (0, h - 1):
            if is_white(x, y):
                stack.append((x, y))
    for y in range(0, h, step_y):
        for x in (0, w - 1):
            if is_white(x, y):
                stack.append((x, y))

    fill = (15, 23, 42, 255)  # slate-950
    while stack:
        x, y = stack.pop()
        if (x, y) in visited or not (0 <= x < w and 0 <= y < h):
            continue
        if not is_white(x, y):
            continue
        visited.add((x, y))
        pixels[x, y] = fill
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return im


def load_source(url: str) -> bytes:
    if url.startswith("/"):
        path = ROOT / "web" / "public" / url.lstrip("/")
        return path.read_bytes()
    return client.get(url).content


def local_name(code: str) -> str:
    return f"{code.replace('+', 'plus')}.png"


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    suspects = json.loads((OUT / "pack_suspects.json").read_text(encoding="utf-8"))
    # also re-process any already-local that still had white
    codes = {r["code"] for r in suspects if "white_bg" in r["issues"] or "soft_white" in r["issues"]}
    # map current url from KR_SETS
    by_code = {s.code: s for s in KR_SETS}

    fixes: dict[str, str] = {}
    for code in sorted(codes):
        s = by_code[code]
        url = s.box_image_kr
        print(f"{code}: {url[-55:]}")
        data = load_source(url)
        im = Image.open(io.BytesIO(data))
        out = whiten_to_black(im)
        path = PUBLIC / local_name(code)
        out.save(path, optimize=True)
        fixes[code] = f"/set-boxes/{path.name}"
        print(f"  -> {path.name} ({path.stat().st_size})")

    updated: list[KrSet] = []
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
    print(f"\nchanged {len(changed)} / processed {len(fixes)}")
    for code, name, url in changed:
        print(f"  {code} {name} -> {url}")


if __name__ == "__main__":
    main()
