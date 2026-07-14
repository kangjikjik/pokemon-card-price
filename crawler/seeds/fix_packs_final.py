"""문제 팩 전수 교체 — 단일 팩 썸네일만 + 체커/흰배경 제거"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import httpx
from PIL import Image

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "final_packs"
AUDIT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
BG = (15, 23, 42, 255)

# 육안 확인된 단일 팩 제품샷 (포스터/배너 아님)
PACK_URLS: dict[str, str] = {
    "SM8": "https://data1.pokemonkorea.co.kr/2018/11/2018-11-06_11-51-00-98193-1541472660.JPG",
    "SM7": "https://data1.pokemonkorea.co.kr/2018/10/2018-10-08_19-57-06-78252-1538996226.JPG",
    "SM6b": "https://data1.pokemonkorea.co.kr/2018/07/2018-07-17_18-24-50-70357-1531819490.png",
    "SM6": "https://data1.pokemonkorea.co.kr/2018/05/2018-05-25_18-22-58-38459-1527240178.png",
    "SM6a": "https://data1.pokemonkorea.co.kr/2018/06/2018-06-22_18-47-50-16043-1529660870.png",
    "SM2+": "https://data1.pokemonkorea.co.kr/2017/10/2017-10-24_18-33-58-94770-1508837638.png",
    "SM1+": "https://data1.pokemonkorea.co.kr/2017/05/2017-05-18_18-45-01-25775-1495100701.png",
    "SM4a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "SM7a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "CP6": "https://data1.pokemonkorea.co.kr/2016/09/2016-09-20_13-45-22-59022-1474346722.jpg",
    "XY8a": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY10_main_OuZo_4.jpg",
    "XY9": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY9_main_2.jpg",
    "XY7": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY7_main_3.jpg",
    "XY6": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY6_main_2.jpg",
    "XY4": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY4_main_5.jpg",
    "XY3": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY3_main_6.jpg",
    "XY2": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY2_main_7.jpg",
    "EBB1": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_ex_battle_boost.png",
    "XY5": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_mc.png",
    "XY3a": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_plazmagail.png",
    "BW4": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_darkrush.png",
    "S2": "https://data1.pokemonkorea.co.kr/2020/04/2020-04-09_15-43-53-72986-1586414633.png",
    "S1a": "https://data1.pokemonkorea.co.kr/2020/03/2020-03-19_17-16-22-65387-1584605782.png",
}

# (url, side) side=left|right|full
DUALS: dict[str, tuple[str, str]] = {
    "XY5a": ("http://pokemonkorea.co.kr/templates/default/content_image/card/XY5_main.jpg", "left"),
    "XY5b": ("http://pokemonkorea.co.kr/templates/default/content_image/card/XY5_main.jpg", "right"),
    "XY11": ("https://data1.pokemonkorea.co.kr/2016/07/2016-07-22_17-32-13-69898-1469176333.jpg", "left"),
    # 소드/실드 — VMAX 안내 포스터 속 팩 크롭
    "S1W": ("https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png", "box:920,1295,1105,1665"),
    "S1H": ("https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png", "box:920,1865,1105,2235"),
}


def is_bg_pixel(r: int, g: int, b: int, a: int) -> bool:
    if a < 40:
        return True
    # pure / near white
    if r >= 230 and g >= 230 and b >= 230:
        return True
    # checkerboard grays (classic transparency preview)
    if abs(r - g) <= 12 and abs(g - b) <= 12:
        if 85 <= r <= 210:
            return True
    # light fringe
    mx, mn = max(r, g, b), min(r, g, b)
    if mx >= 240 and mx - mn <= 18:
        return True
    return False


def to_dark_pack(im: Image.Image, pad_ratio: float = 0.06) -> Image.Image:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()

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
        r, g, b, a = px[x, y]
        if not is_bg_pixel(r, g, b, a):
            continue
        visited.add((x, y))
        px[x, y] = (0, 0, 0, 0)
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    # also punch remaining checker islands in outer 12% margin
    mx = max(1, int(w * 0.12))
    my = max(1, int(h * 0.12))
    for x in range(w):
        for y in list(range(0, my)) + list(range(h - my, h)):
            r, g, b, a = px[x, y]
            if is_bg_pixel(r, g, b, a):
                px[x, y] = (0, 0, 0, 0)
    for y in range(h):
        for x in list(range(0, mx)) + list(range(w - mx, w)):
            r, g, b, a = px[x, y]
            if is_bg_pixel(r, g, b, a):
                px[x, y] = (0, 0, 0, 0)

    bbox = rgba.getbbox()
    if not bbox:
        return Image.new("RGBA", (512, 512), BG)
    subject = rgba.crop(bbox)
    sw, sh = subject.size
    pad = int(max(sw, sh) * pad_ratio)
    side = max(sw + pad * 2, sh + pad * 2)
    canvas = Image.new("RGBA", (side, side), BG)
    canvas.paste(subject, ((side - sw) // 2, (side - sh) // 2), subject)
    return canvas


def load_source(code: str) -> Image.Image:
    if code in DUALS:
        url, how = DUALS[code]
        data = client.get(url).content
        im = Image.open(io.BytesIO(data))
        if how.startswith("box:"):
            x0, y0, x1, y1 = map(int, how[4:].split(","))
            return im.crop((x0, y0, x1, y1))
        w, h = im.size
        mid = w // 2
        return im.crop((0, 0, mid, h) if how == "left" else (mid, 0, w, h))
    url = PACK_URLS[code]
    data = client.get(url).content
    return Image.open(io.BytesIO(data))


def local_name(code: str) -> str:
    return f"{code.replace('+', 'plus')}.png"


def ring_white(path: Path) -> float:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    ring = []
    for x in range(w):
        for y in (0, 1, 2, h - 1, h - 2, max(0, h - 3)):
            ring.append(im.getpixel((x, min(y, h - 1))))
    for y in range(h):
        for x in (0, 1, 2, w - 1, w - 2, max(0, w - 3)):
            ring.append(im.getpixel((min(x, w - 1), y)))
    return sum(1 for r, g, b in ring if r >= 235 and g >= 235 and b >= 235) / len(ring)


def has_checker(path: Path) -> bool:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    samples = [im.getpixel((x, y)) for x in range(0, min(80, w), 3) for y in range(0, min(80, h), 3)]
    light = sum(1 for r, g, b in samples if 170 <= r <= 210 and abs(r - g) < 12 and abs(g - b) < 12)
    dark = sum(1 for r, g, b in samples if 90 <= r <= 145 and abs(r - g) < 12 and abs(g - b) < 12)
    return light > 6 and dark > 6


def main():
    codes = sorted(set(PACK_URLS) | set(DUALS))
    results = {}
    for code in codes:
        print(f"\n=== {code} ===")
        try:
            raw = load_source(code)
            print(f"  src {raw.size} mode={raw.mode}")
            out = to_dark_pack(raw)
            path = PUBLIC / local_name(code)
            out.save(path, optimize=True)
            out.save(AUDIT / f"{code}.png", optimize=True)
            wr = ring_white(path)
            ch = has_checker(path)
            ar = out.size[1] / out.size[0]
            ok = wr < 0.12 and not ch and ar < 1.85
            results[code] = {"ok": ok, "size": out.size, "ring_white": round(wr, 3), "checker": ch, "ar": round(ar, 2)}
            print(f"  -> {path.name} {out.size} white={wr:.3f} checker={ch} ok={ok}")
        except Exception as e:
            print(f"  FAIL {e}")
            results[code] = {"ok": False, "error": str(e)}

    fixes = {c: f"/set-boxes/{local_name(c)}" for c in codes if (PUBLIC / local_name(c)).exists()}
    updated = []
    for s in KR_SETS:
        if s.code in fixes:
            updated.append(KrSet(s.code, s.name_kr, s.released_at, fixes[s.code], s.box_image_jp))
        else:
            updated.append(s)
    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images({s.code: s.box_image_kr for s in updated if s.box_image_kr})

    failed = [c for c, r in results.items() if not r.get("ok")]
    print(f"\nDONE ok={sum(1 for r in results.values() if r.get('ok'))} fail={failed}")
    Path("_audit_out/final_pack_fix.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
