"""팩 이미지 v4 — flood fill 금지. 비배경 bbox 크롭 후 다크 캔버스."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import httpx
from PIL import Image

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from fix_packs_final import PACK_URLS, DUALS, local_name
from fix_packs_v2 import pick_s1a
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "final_packs"
AUDIT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
BG = (15, 23, 42)


def is_studio(r: int, g: int, b: int) -> bool:
    chroma = max(r, g, b) - min(r, g, b)
    if chroma <= 10 and min(r, g, b) >= 245:
        return True
    if chroma <= 8 and 115 <= r <= 215 and abs(r - g) <= 6 and abs(g - b) <= 6:
        return True
    return False


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


def to_dark_pack(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    xs: list[int] = []
    ys: list[int] = []
    for y in range(h):
        for x in range(w):
            r, g, b = rgb.getpixel((x, y))
            if not is_studio(r, g, b):
                xs.append(x)
                ys.append(y)
    if not xs:
        canvas = Image.new("RGB", (320, 320), BG)
        return canvas

    pad = 2
    x0 = max(0, min(xs) - pad)
    y0 = max(0, min(ys) - pad)
    x1 = min(w, max(xs) + pad + 1)
    y1 = min(h, max(ys) + pad + 1)
    subject = rgb.crop((x0, y0, x1, y1))
    sw, sh = subject.size

    # replace remaining studio pixels in subject with BG (only pure studio, no chroma)
    sp = subject.load()
    for y in range(sh):
        for x in range(sw):
            r, g, b = sp[x, y]
            if is_studio(r, g, b):
                sp[x, y] = BG

    margin = int(max(sw, sh) * 0.05)
    side = max(sw + margin * 2, sh + margin * 2, 320)
    canvas = Image.new("RGB", (side, side), BG)
    canvas.paste(subject, ((side - sw) // 2, (side - sh) // 2))
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
        print(f"  {out.size} corner={out.getpixel((2,2))}")

    updated = []
    for s in KR_SETS:
        if s.code in codes and (PUBLIC / local_name(s.code)).exists():
            updated.append(
                KrSet(
                    s.code, s.name_kr, s.released_at, f"/set-boxes/{local_name(s.code)}",
                    s.bs_code, s.collectory_id, s.msrp_pack_kr, s.msrp_box_kr, s.pokemoncard_page,
                )
            )
        else:
            updated.append(s)
    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images(updated)
    print("synced")


if __name__ == "__main__":
    main()
