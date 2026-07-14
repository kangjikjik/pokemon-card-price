"""팩 배경 제거 v3 — 가장자리 flood + 알파 팽창으로 팩 가장자리 복원"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageFilter

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from fix_packs_final import PACK_URLS, DUALS, local_name
from fix_packs_v2 import pick_s1a, is_studio_bg
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "final_packs"
AUDIT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
BG = (15, 23, 42, 255)


def load_source(code: str) -> Image.Image:
    if code == "S1a":
        return pick_s1a()
    if code in DUALS:
        url, how = DUALS[code]
        im = Image.open(io.BytesIO(client.get(url).content))
        if how.startswith("box:"):
            x0, y0, x1, y1 = map(int, how[4:].split(","))
            return im.crop((x0, y0, x1, y1))
        w, h = im.size
        mid = w // 2
        return im.crop((0, 0, mid, h) if how == "left" else (mid, 0, w, h))
    return Image.open(io.BytesIO(client.get(PACK_URLS[code]).content))


def is_studio_bg(r: int, g: int, b: int, a: int) -> bool:
    """스튜디오 배경만 — 채도 있는 밝은 픽셀(번개 등)은 절대 제거하지 않음."""
    if a < 30:
        return True
    chroma = max(r, g, b) - min(r, g, b)
    # pure white / near-white gray only
    if chroma <= 10 and min(r, g, b) >= 245:
        return True
    # checkerboard gray tiles
    if chroma <= 8 and 115 <= r <= 215 and abs(r - g) <= 6 and abs(g - b) <= 6:
        return True
    return False


def to_dark_pack(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    visited: set[tuple[int, int]] = set()
    stack: list[tuple[int, int]] = []
    for x in range(w):
        stack += [(x, 0), (x, h - 1)]
    for y in range(h):
        stack += [(0, y), (w - 1, y)]

    while stack:
        x, y = stack.pop()
        if (x, y) in visited or not (0 <= x < w and 0 <= y < h):
            continue
        r, g, b, a = px[x, y]
        if not is_studio_bg(r, g, b, a):
            continue
        visited.add((x, y))
        px[x, y] = (0, 0, 0, 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    # restore pack edge anti-alias eaten by flood (dilate alpha)
    r, g, b, a = rgba.split()
    a = a.filter(ImageFilter.MaxFilter(3))
    rgba = Image.merge("RGBA", (r, g, b, a))

    # re-clear pure studio white that dilation may have pulled back at corners
    px = rgba.load()
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        # small corner cleanup
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h:
                    rr, gg, bb, aa = px[xx, yy]
                    if is_studio_bg(rr, gg, bb, aa):
                        px[xx, yy] = (0, 0, 0, 0)

    bbox = rgba.getbbox()
    if not bbox:
        return Image.new("RGBA", (512, 512), BG)
    subject = rgba.crop(bbox)
    sw, sh = subject.size
    pad = int(max(sw, sh) * 0.04)
    side = max(sw + pad * 2, sh + pad * 2, 320)
    canvas = Image.new("RGBA", (side, side), BG)
    canvas.paste(subject, ((side - sw) // 2, (side - sh) // 2), subject)
    return canvas


def main():
    codes = sorted(set(PACK_URLS) | set(DUALS))
    for code in codes:
        print(f"=== {code} ===")
        raw = load_source(code)
        out = to_dark_pack(raw)
        path = PUBLIC / local_name(code)
        out.save(path, optimize=True)
        out.save(AUDIT / local_name(code), optimize=True)
        rgb = out.convert("RGB")
        print(f"  {out.size} corner={rgb.getpixel((2,2))}")

    updated = []
    for s in KR_SETS:
        loc = f"/set-boxes/{local_name(s.code)}"
        if (PUBLIC / local_name(s.code)).exists() and s.code in codes:
            updated.append(
                KrSet(
                    s.code, s.name_kr, s.released_at, loc,
                    s.bs_code, s.collectory_id, s.msrp_pack_kr, s.msrp_box_kr, s.pokemoncard_page,
                )
            )
        else:
            updated.append(s)
    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images(updated)
    print("synced kr_sets + set-images")


if __name__ == "__main__":
    main()
