"""Download store pack photos + rembg cleanup for S1W/S1H."""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import httpx
from PIL import Image
from rembg import remove

from fix_packs_v5 import to_dark_pack

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "fix_round2"
client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

store_pages = {
    "S1W": [
        "https://www.japan2uk.com/products/pokemon-sword-s1w-korean-booster-pack",
        "https://koreantoyshop.com/pokemon-cards-sword-v-booster-1-box-s1w-30-packs-5-cards-sword-shield-korean/",
        "https://eclipsegames.com.au/products/pokemon-tcg-s1w-sword-v-booster-box-korean",
    ],
    "S1H": [
        "https://www.japan2uk.com/products/pokemon-shield-s1h-korean-booster-pack",
        "https://koreantoyshop.com/pokemon-cards-shield-v-booster-1-box-s1h-30-packs-5-cards-sword-shield-korean/",
    ],
}


def scrape_imgs(url: str) -> list[str]:
    r = client.get(url)
    print(f"  page {r.status_code} {url}")
    if r.status_code != 200:
        return []
    found = re.findall(r'(?:src|data-src|href)=["\']([^"\']+\.(?:png|jpg|jpeg|webp))', r.text, re.I)
    found += re.findall(r'https?://[^"\'\s>]+\.(?:png|jpg|jpeg|webp)', r.text, re.I)
    out = []
    seen = set()
    for s in found:
        if s.startswith("//"):
            s = "https:" + s
        if any(x in s.lower() for x in ("logo", "icon", "sprite", "payment", "flag", "avatar")):
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def rembg_to_dark(im: Image.Image) -> Image.Image:
    cut = remove(im.convert("RGBA"))
    # composite on dark
    bg = Image.new("RGBA", cut.size, (15, 23, 42, 255))
    composed = Image.alpha_composite(bg, cut).convert("RGB")
    return to_dark_pack(composed)


def try_from_poster_rembg():
    poster = Image.open(
        io.BytesIO(
            client.get(
                "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png"
            ).content
        )
    )
    boxes = {"S1W": (900, 1260, 1160, 1660), "S1H": (900, 1845, 1160, 2245)}
    for code, box in boxes.items():
        raw = poster.crop(box)
        raw.save(AUDIT / f"rembg_in_{code}.png")
        out = rembg_to_dark(raw)
        out.save(AUDIT / f"rembg_out_{code}.png")
        out.save(PUBLIC / f"{code}.png", optimize=True)
        print(f"  rembg poster {code} -> {out.size}")


def main():
    print("=== rembg from poster ===")
    try_from_poster_rembg()

    print("=== store scrape ===")
    for code, pages in store_pages.items():
        for page in pages:
            for i, src in enumerate(scrape_imgs(page)[:20]):
                try:
                    resp = client.get(src)
                    if "image" not in resp.headers.get("content-type", ""):
                        continue
                    im = Image.open(io.BytesIO(resp.content))
                    if min(im.size) < 80 or max(im.size) > 4000:
                        continue
                    print(f"  {code} [{i}] {im.size} {src[:100]}")
                    im.save(AUDIT / f"store_{code}_{i}_{im.size[0]}x{im.size[1]}.png")
                except Exception as e:
                    print("   err", e)


if __name__ == "__main__":
    main()
