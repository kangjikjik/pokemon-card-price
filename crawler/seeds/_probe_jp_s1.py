"""Find clean S1W/S1H pack images from JP site / other CDNs."""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import httpx
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
AUDIT = Path(__file__).parent / "_img_audit" / "fix_round2"
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

pages = [
    "https://www.pokemon-card.com/products/s/s1.html",
    "https://www.pokemon-card.com/products/s/s1a.html",
]

for u in pages:
    r = client.get(u)
    print(f"\n=== {u} status={r.status_code} len={len(r.text)} ===")
    imgs = re.findall(r'(?:src|href)=["\']([^"\']+\.(?:png|jpg|jpeg|webp))', r.text, re.I)
    imgs += re.findall(r'https?://[^"\'\s>]+\.(?:png|jpg|jpeg|webp)', r.text, re.I)
    seen = set()
    for i, src in enumerate(imgs):
        if src in seen:
            continue
        seen.add(src)
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://www.pokemon-card.com" + src
        if "logo" in src.lower() or "icon" in src.lower() or "common" in src.lower():
            continue
        try:
            resp = client.get(src)
            if "image" not in resp.headers.get("content-type", ""):
                continue
            im = Image.open(io.BytesIO(resp.content))
            print(f"  {im.size} {src}")
            if 100 < min(im.size) < 2000 and max(im.size) < 3000:
                name = f"jp_{u.split('/')[-1].replace('.html','')}_{i}_{im.size[0]}x{im.size[1]}.png"
                im.save(AUDIT / name)
        except Exception as e:
            print("  err", src[:80], e)

# try known product image patterns on pokemon-card.com
candidates = [
    "https://www.pokemon-card.com/assets/images/card_images/products/S1/pack_s1W.jpg",
    "https://www.pokemon-card.com/assets/images/card_images/products/S1/pack_s1H.jpg",
    "https://www.pokemon-card.com/assets/images/product_image/products/S1/S1_pack.jpg",
    "https://www.pokemon-card.com/assets/images/card_images/products/SM/sm1_pack.jpg",
]
print("\n=== pattern tries ===")
for u in candidates:
    r = client.get(u)
    print(u.split("/")[-1], r.status_code, r.headers.get("content-type"), len(r.content))
