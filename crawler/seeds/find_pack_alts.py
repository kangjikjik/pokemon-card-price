"""S6H 등 흰배경/잘못된 팩 — pokemoncard 페이지 후보"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
from kr_sets import KR_BY_CODE
from resolve_legacy_box_images import DATA1_IMG, MAIN_IMG, PLACEHOLDER

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "_img_audit"
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

CODES = ["S6H", "S3H", "S3Z", "S2R", "S2", "S1a", "S4SV", "CEL"]

for code in CODES:
    s = KR_BY_CODE[code]
    print(f"\n=== {code} {s.name_kr} p{s.pokemoncard_page} ===")
    print(f"stored: {s.box_image_kr}")
    if not s.pokemoncard_page:
        continue
    r = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}")
    r.encoding = "utf-8"
    imgs = list(dict.fromkeys(
        [u for u in DATA1_IMG.findall(r.text) if PLACEHOLDER not in u] + MAIN_IMG.findall(r.text)
    ))
    for i, u in enumerate(imgs[:10]):
        print(f"  [{i}] {u}")
        try:
            ir = client.get(u)
            ext = Path(u.split("?")[0]).suffix or ".png"
            (OUT / f"alt_{code}_{i}{ext}").write_bytes(ir.content)
        except Exception as e:
            print(f"    fail {e}")
