"""SM7a REMASTER 후보 이미지 다운로드·비교 후 올바른 팩 적용"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import httpx
from PIL import Image

from fix_white_canvas import to_black_canvas, ring_whiteness

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "_img_audit" / "sm7a_cands"
OUT.mkdir(parents=True, exist_ok=True)
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

CANDS = {
    "c1_sync": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-27_09-35-24-10929-1511742924.jpg",
    "c2_featured": "https://data1.pokemonkorea.co.kr/2017/12/2017-12-08_17-21-07-46128-1512721267.jpg",
    "c3_old": "https://data1.pokemonkorea.co.kr/2017/12/2017-12-13_10-44-40-86175-1513129480.jpg",
    "sm4a_pack": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
}

for name, url in CANDS.items():
    print(f"fetch {name}")
    r = client.get(url)
    print(f"  status={r.status_code} bytes={len(r.content)}")
    if r.status_code >= 400:
        continue
    path = OUT / f"{name}.jpg"
    if r.content[:4] == b"\x89PNG":
        path = OUT / f"{name}.png"
    path.write_bytes(r.content)
    im = Image.open(io.BytesIO(r.content))
    print(f"  size={im.size} mode={im.mode}")

# Prefer remaster-specific if visually different from SM4a
sm4 = Image.open(io.BytesIO(client.get(CANDS["sm4a_pack"]).content)).convert("RGB")
chosen = None
for name in ["c1_sync", "c3_old", "c2_featured"]:
    matches = list(OUT.glob(f"{name}.*"))
    if not matches:
        continue
    im = Image.open(matches[0]).convert("RGB")
    # skip if identical dimensions+hash-ish to sm4a (same pack art)
    # remaster often has "REMASTER" text or different layout
    # use file difference: resize and mse
    a = sm4.resize((200, 200))
    b = im.resize((200, 200))
    mse = sum((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2 + (pa[2] - pb[2]) ** 2 for pa, pb in zip(a.getdata(), b.getdata())) / (200 * 200 * 3)
    print(f"  mse vs SM4a {name}: {mse:.1f}")
    if mse > 500:
        chosen = matches[0]
        print(f"  SELECT {name}")
        break

if not chosen:
    # fallback to c1 even if similar — keep SM4a as SM4a, use c1 for SM7a if available
    matches = list(OUT.glob("c1_sync.*"))
    chosen = matches[0] if matches else None
    print(f"fallback {chosen}")

if chosen:
    out = to_black_canvas(Image.open(chosen))
    dest = PUBLIC / "SM7a.png"
    out.save(dest, optimize=True)
    print(f"wrote {dest} ring={ring_whiteness(dest):.3f} size={dest.stat().st_size}")
