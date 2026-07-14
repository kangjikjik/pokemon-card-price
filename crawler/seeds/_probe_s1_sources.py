"""Find S1 pack sources and verify SM dual mapping."""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import httpx
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
AUDIT = Path(__file__).parent / "_img_audit" / "fix_round2"
AUDIT.mkdir(parents=True, exist_ok=True)

pages = [
    "https://pokemonkorea.co.kr/news/6/286",
    "https://pokemonkorea.co.kr/news/6/178",
    "https://pokemonkorea.co.kr/news/6/177",
]

for u in pages:
    r = client.get(u)
    imgs = re.findall(
        r"https://data1\.pokemonkorea\.co\.kr/[^\s\"']+\.(?:png|jpg|jpeg)",
        r.text,
        re.I,
    )
    # unique preserve order
    seen = set()
    uniq = []
    for i in imgs:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    print(f"\n=== {u} ({len(uniq)}) ===")
    for i, url in enumerate(uniq):
        try:
            im = Image.open(io.BytesIO(client.get(url).content))
            print(f"  [{i}] {im.size} {url.split('/')[-1][:60]}")
            if im.size[0] * im.size[1] < 800_000:
                im.save(AUDIT / f"cand_{u.split('/')[-1]}_{i}_{im.size[0]}x{im.size[1]}.png")
        except Exception as e:
            print(f"  [{i}] ERR {e} {url[:80]}")

# also try known JP pack-style assets / store
jp_tries = [
    "https://www.pokemon-card.com/assets/images/card_images/products/S1W/S1W.jpg",
    "https://www.pokemon-card.com/assets/images/products/expansion/S1W.jpg",
]
print("\n=== JP tries ===")
for u in jp_tries:
    try:
        r = client.get(u)
        print(u, r.status_code, r.headers.get("content-type"), len(r.content))
    except Exception as e:
        print(u, e)
