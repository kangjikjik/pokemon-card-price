"""박스 이미지 후보 수집 — pokemoncard 페이지 + collectory"""
from __future__ import annotations

import httpx

from kr_sets import KR_SETS, KR_BY_CODE

CODES = ["SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM7a", "SM12", "SM2+"]

r = httpx.get("https://collectory.cc/api/sets", timeout=60)
by_id = {s["id"]: s for s in r.json().get("sets") or []}

for code in CODES:
    s = KR_BY_CODE[code]
    m = by_id.get(s.collectory_id) or {}
    print(f"\n{code} collectory: {m.get('image_url', 'NONE')}")
    print(f"  stored: {s.box_image_kr}")
