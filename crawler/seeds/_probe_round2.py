"""문제 팩 후보 이미지 조사"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import httpx
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "_img_audit" / "fix_round2"
OUT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
IMG = re.compile(
    r"(https?://(?:data1\.pokemonkorea\.co\.kr|pokemonkorea\.co\.kr)[^\"'\s>]+\.(?:png|jpg|jpeg|PNG|JPG|JPEG))",
    re.I,
)

PAGES = {
    "S1WH": 286,
    "SM12a": 271,
    "SM9": 166,
    "SM8b": 163,
    "SM4": 124,
    "SM1": 99,
    "CP6": 89,
}

for code, page in PAGES.items():
    print(f"\n==== {code} page {page} ====")
    html = client.get(f"https://pokemoncard.co.kr/card/{page}").text
    urls = []
    seen = set()
    for u in IMG.findall(html):
        if u in seen:
            continue
        seen.add(u)
        low = u.lower()
        if any(x in low for x in ("hover", "banner", "bg_", "gms", "1920", "wide")):
            continue
        urls.append(u)
    for i, u in enumerate(urls[:18]):
        try:
            data = client.get(u).content
            im = Image.open(io.BytesIO(data))
            w, h = im.size
            ar = h / w if w else 0
            print(f"  [{i}] {w:4}x{h:<4} ar={ar:.2f} {u}")
            if 0.85 <= ar <= 1.4 and 200 <= min(w, h) <= 1200:
                ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
                (OUT / f"{code}_{i}{ext}").write_bytes(data)
        except Exception as e:
            print(f"  fail {e}")
