"""문제 세트별 후보 URL 비율 점검"""
from __future__ import annotations

import re
import struct
import httpx
from kr_sets import KR_BY_CODE
from resolve_legacy_box_images import DATA1_IMG, MAIN_IMG, PLACEHOLDER

client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})


def dims(url):
    try:
        r = client.get(url)
        d = r.content[:65536]
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", d[16:24])
            return w, h
        if d.startswith(b"\xff\xd8"):
            i = 2
            while i < len(d):
                while i < len(d) and d[i] == 0xFF:
                    i += 1
                m = d[i]
                i += 1
                if m in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">HH", d[i + 3 : i + 7])
                    return w, h
                seg = struct.unpack(">H", d[i : i + 2])[0]
                i += seg
    except Exception:
        pass
    return 0, 0


CODES = [
    "S2", "S1W", "S1H", "SM12a", "SM12", "SM10", "SM9a", "SM6a",
    "SM5+", "SM4+", "SM4", "SM4a", "SM7a", "CP6", "XY8a", "SM2+",
    "SM1M", "SM1C",
]

for code in CODES:
    s = KR_BY_CODE[code]
    r = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}")
    r.encoding = "utf-8"
    imgs = list(dict.fromkeys(DATA1_IMG.findall(r.text) + MAIN_IMG.findall(r.text)))
    imgs = [u for u in imgs if PLACEHOLDER not in u]
    scored = []
    for u in imgs:
        w, h = dims(u)
        if not w:
            continue
        ratio = w / h
        # product box: portrait or near-square, not banner
        score = 0
        if ratio > 1.3:
            score -= 20
        elif ratio < 0.9:
            score += 10
        else:
            score += 15
        if u.lower().endswith(".png"):
            score += 3
        if "main" in u.lower():
            score += 5
        if "hover" in u.lower() or "gms" in u.lower():
            score -= 30
        scored.append((score, w, h, u))
    scored.sort(reverse=True)
    print(f"\n=== {code} p{s.pokemoncard_page} ===")
    print(f"stored: {s.box_image_kr.split('/')[-1]}")
    for sc, w, h, u in scored[:6]:
        print(f"  {sc:3} {w:4}x{h:<4} {u.split('/')[-1]}")
