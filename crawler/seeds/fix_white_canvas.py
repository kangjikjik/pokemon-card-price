"""흰 배경 팩 — 검정 캔버스 합성으로 강제 재처리"""
from __future__ import annotations

import io
import json
import os
import sys
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
OUT = Path(__file__).parent / "_audit_out"
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
BG = (15, 23, 42, 255)  # slate-950


def to_black_canvas(im: Image.Image, threshold: int = 230, pad_ratio: float = 0.04) -> Image.Image:
    """흰/밝은 스튜디오 배경을 제거하고 슬레이트 캔버스에 팩만 올린다."""
    rgba = im.convert("RGBA")
    w, h = rgba.size
    pixels = rgba.load()

    def is_bg(x: int, y: int) -> bool:
        r, g, b, a = pixels[x, y]
        if a < 40:
            return True
        # near-white / light gray studio
        if r >= threshold and g >= threshold and b >= threshold:
            return True
        # very light with low chroma
        mx, mn = max(r, g, b), min(r, g, b)
        if mx >= 245 and mx - mn <= 12:
            return True
        return False

    # flood from edges
    visited: set[tuple[int, int]] = set()
    stack: list[tuple[int, int]] = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in visited or not (0 <= x < w and 0 <= y < h):
            continue
        if not is_bg(x, y):
            continue
        visited.add((x, y))
        pixels[x, y] = (0, 0, 0, 0)
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    # bounding box of remaining opaque content
    bbox = rgba.getbbox()
    if not bbox:
        canvas = Image.new("RGBA", (w, h), BG)
        return canvas

    subject = rgba.crop(bbox)
    sw, sh = subject.size
    pad = int(max(sw, sh) * pad_ratio)
    cw, ch = sw + pad * 2, sh + pad * 2
    # keep roughly square-ish for grid
    side = max(cw, ch)
    canvas = Image.new("RGBA", (side, side), BG)
    ox = (side - sw) // 2
    oy = (side - sh) // 2
    canvas.paste(subject, (ox, oy), subject)
    return canvas


def ring_whiteness(path: Path) -> float:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    ring = []
    for x in range(w):
        for y in range(min(3, h)):
            ring.append(im.getpixel((x, y)))
        for y in range(max(0, h - 3), h):
            ring.append(im.getpixel((x, y)))
    for y in range(h):
        for x in range(min(3, w)):
            ring.append(im.getpixel((x, y)))
        for x in range(max(0, w - 3), w):
            ring.append(im.getpixel((x, y)))
    return sum(1 for r, g, b in ring if r >= 235 and g >= 235 and b >= 235) / len(ring)


def load_source(url: str) -> bytes:
    if url.startswith("/"):
        # prefer original remote if we stored only broken local — try pokemoncard from suspects audit
        path = ROOT / "web" / "public" / url.lstrip("/")
        return path.read_bytes()
    return client.get(url).content


def local_name(code: str) -> str:
    return f"{code.replace('+', 'plus')}.png"


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    # process any local with white ring OR listed suspects
    suspects = json.loads((OUT / "pack_suspects.json").read_text(encoding="utf-8"))
    codes = {r["code"] for r in suspects}
    by_code = {s.code: s for s in KR_SETS}

    # also scan all local set-boxes referenced by KR_SETS
    for s in KR_SETS:
        url = s.box_image_kr or ""
        if url.startswith("/set-boxes/"):
            p = PUBLIC / Path(url).name
            if p.exists() and ring_whiteness(p) >= 0.15:
                codes.add(s.code)

    fixes: dict[str, str] = {}
    for code in sorted(codes):
        s = by_code[code]
        url = s.box_image_kr
        print(f"{code}: {url}")
        data = load_source(url)
        im = Image.open(io.BytesIO(data))
        out = to_black_canvas(im)
        path = PUBLIC / local_name(code)
        out.save(path, optimize=True)
        wr = ring_whiteness(path)
        fixes[code] = f"/set-boxes/{path.name}"
        print(f"  -> {path.name} ring_white={wr:.3f} size={path.stat().st_size}")

    updated: list[KrSet] = []
    changed = []
    for s in KR_SETS:
        if s.code in fixes:
            nu = fixes[s.code]
            if s.box_image_kr != nu:
                changed.append(f"{s.code} {s.name_kr} -> {nu}")
            updated.append(KrSet(s.code, s.name_kr, s.released_at, nu, s.box_image_jp))
        else:
            updated.append(s)

    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images({s.code: s.box_image_kr for s in updated if s.box_image_kr})

    # sync DB image_url
    sets = sb.table("card_sets").select("id,set_code").execute().data or []
    by_db = {s["set_code"]: s["id"] for s in sets}
    for code, url in fixes.items():
        sid = by_db.get(code)
        if sid:
            sb.table("card_sets").update({"image_url": url}).eq("id", sid).execute()

    print(f"\nfixed {len(fixes)} packs, kr_sets changed {len(changed)}")
    for c in changed[:30]:
        print(" ", c)


if __name__ == "__main__":
    main()
