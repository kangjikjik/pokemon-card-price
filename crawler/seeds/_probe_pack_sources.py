"""pokemoncard 페이지에서 후보 이미지 점수 매기고 미리보기 저장"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import httpx
from PIL import Image

from refix_bad_packs import IMG_RE, PAGES, score_pack, fetch_page_candidates

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "_img_audit" / "page_cands"
OUT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

# also try collectory
from collectory_map import COLLECTORY_SETS

focus = ["SM8", "SM7", "SM6b", "SM6", "SM1+", "SM2+", "CP6", "XY11", "XY5a", "S1a", "S1W", "S1H"]

for code in focus:
    print(f"\n==== {code} ====")
    urls = []
    if code in PAGES:
        urls.extend(fetch_page_candidates(PAGES[code]))
    cfg = COLLECTORY_SETS.get(code) or COLLECTORY_SETS.get(code.replace("+", "plus"))
    # collectory map keys
    for k, v in COLLECTORY_SETS.items():
        if k == code or k.replace("+", "") == code.replace("+", ""):
            try:
                meta = client.get(f"https://collectory.cc/api/sets").json()
            except Exception:
                meta = {}
            break
    # direct collectory set image if mapped
    if code in COLLECTORY_SETS:
        sid = COLLECTORY_SETS[code]["id"]
        try:
            sets = client.get("https://collectory.cc/api/sets", timeout=30).json().get("sets") or []
            for s in sets:
                if s.get("id") == sid and s.get("image_url"):
                    urls.insert(0, s["image_url"])
                    print(f"  collectory img: {s['image_url']}")
        except Exception as e:
            print(f"  collectory err {e}")

    print(f"  candidates {len(urls)}")
    ranked = []
    for i, u in enumerate(urls[:12]):
        try:
            data = client.get(u).content
            im = Image.open(io.BytesIO(data))
            sc = score_pack(im)
            ranked.append((sc, u, im.size, data))
            print(f"  {sc:6.1f} {im.size} {u[-75:]}")
        except Exception as e:
            print(f"  fail {u[-50:]} {e}")
    ranked.sort(reverse=True)
    if ranked:
        sc, u, sz, data = ranked[0]
        ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        (OUT / f"{code}{ext}").write_bytes(data)
        print(f"  BEST -> {code}{ext} score={sc}")
