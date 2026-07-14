"""팩 이미지 재처리 — 스튜디오 흰/체커만 제거 (팩 본체 보존)"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import httpx
from PIL import Image

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from fix_packs_final import PACK_URLS, DUALS, local_name, load_source
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "final_packs"
AUDIT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
BG = (15, 23, 42, 255)
IMG_RE = re.compile(
    r"(https?://(?:data1\.pokemonkorea\.co\.kr|pokemonkorea\.co\.kr)[^\"'\s>]+\.(?:png|jpg|jpeg|PNG|JPG|JPEG))"
)


def is_studio_bg(r: int, g: int, b: int, a: int) -> bool:
    """팩 포일/흰 패키징과 구분: 완전 흰 + 체커보드 회색만."""
    if a < 30:
        return True
    # pure studio white
    if r >= 250 and g >= 250 and b >= 250:
        return True
    # classic checker tiles (low chroma mid-gray)
    if abs(r - g) <= 8 and abs(g - b) <= 8:
        # two checker levels commonly ~192 and ~128, or ~204/~153
        if 120 <= r <= 210 and max(r, g, b) - min(r, g, b) <= 8:
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

    bbox = rgba.getbbox()
    if not bbox:
        return Image.new("RGBA", (512, 512), BG)
    subject = rgba.crop(bbox)
    sw, sh = subject.size
    pad = int(max(sw, sh) * 0.05)
    side = max(sw + pad * 2, sh + pad * 2, 320)
    canvas = Image.new("RGBA", (side, side), BG)
    canvas.paste(subject, ((side - sw) // 2, (side - sh) // 2), subject)
    return canvas


def pick_s1a() -> Image.Image:
    """VMAX라이징 페이지에서 배너 아닌 팩/제품샷 선택"""
    html = client.get("https://pokemoncard.co.kr/card/291").text
    urls = []
    seen = set()
    for u in IMG_RE.findall(html):
        if u in seen:
            continue
        seen.add(u)
        if any(x in u.lower() for x in ("hover", "banner", "bg_", "gms", "1920")):
            continue
        urls.append(u)
    best = None
    best_sc = -999
    for u in urls:
        try:
            data = client.get(u).content
            im = Image.open(io.BytesIO(data))
        except Exception:
            continue
        w, h = im.size
        ar = h / w if w else 99
        sc = 0
        if 0.85 <= ar <= 1.35 and 200 <= w <= 900:
            sc += 50
        if ar > 2.0:
            sc -= 80
        sc += min(20, (w * h) ** 0.5 / 50)
        print(f"  S1a cand {sc:5.1f} {im.size} {u[-60:]}")
        if sc > best_sc:
            best_sc = sc
            best = im
    if best is None or best_sc < 0:
        raise RuntimeError("S1a pack not found")
    return best


def main():
    codes = sorted(set(PACK_URLS) | set(DUALS))
    results = {}
    for code in codes:
        print(f"\n=== {code} ===")
        try:
            if code == "S1a":
                raw = pick_s1a()
            else:
                raw = load_source(code)
            print(f"  src {raw.size}")
            out = to_dark_pack(raw)
            path = PUBLIC / local_name(code)
            out.save(path, optimize=True)
            out.save(AUDIT / f"{local_name(code)}", optimize=True)
            # corner check
            rgb = out.convert("RGB")
            w, h = rgb.size
            corners = [rgb.getpixel(p) for p in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]]
            white = sum(1 for r, g, b in corners if r > 240)
            ar = h / w
            ok = white == 0 and ar < 1.7 and max(w, h) < 2000
            results[code] = {"ok": ok, "size": [w, h], "corners": corners, "ar": round(ar, 2)}
            print(f"  saved {path.name} {w}x{h} corners={corners} ok={ok}")
        except Exception as e:
            print(f"  FAIL {e}")
            results[code] = {"ok": False, "error": str(e)}

    fixes = {c: f"/set-boxes/{local_name(c)}" for c in codes if (PUBLIC / local_name(c)).exists()}
    updated = []
    for s in KR_SETS:
        if s.code in fixes:
            updated.append(
                KrSet(
                    s.code, s.name_kr, s.released_at, fixes[s.code],
                    s.bs_code, s.collectory_id, s.msrp_pack_kr, s.msrp_box_kr, s.pokemoncard_page,
                )
            )
        else:
            updated.append(s)
    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images({s.code: s.box_image_kr for s in updated if s.box_image_kr})

    failed = [c for c, r in results.items() if not r.get("ok")]
    print(f"\nDONE ok={sum(1 for r in results.values() if r.get('ok'))} fail={failed}")
    Path("_audit_out/final_pack_fix2.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
