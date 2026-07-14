"""Find SM6 108 Energy Porter UR image; verify footers."""
from __future__ import annotations

import re
from pathlib import Path

import httpx

OUT = Path(__file__).with_name("_audit_out") / "sm5plus_imgs"
OUT.mkdir(parents=True, exist_ok=True)
c = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

pages = [
    "http://jp.pokellector.com/Japanese-Forbidden-Light-Expansion/Eneporter-Card-108",
    "http://jp.pokellector.com/Japanese-Forbidden-Light-Expansion/Mystery-Treasure-Card-109",
    "https://www.serebii.net/card/forbiddenlight/eneporter.shtml",
]
for url in pages:
    r = c.get(url)
    print("PAGE", r.status_code, url)
    imgs = re.findall(r'(?:src|data-src|content)="([^"]+)"', r.text)
    for m in imgs:
        if any(x in m.lower() for x in ("108", "109", "card", "jpg", "png", "webp", "large")):
            print(" ", m)

cands = [
    "http://jp.pokellector.com/static/images/cards/Japanese-Forbidden-Light/108.jpg",
    "https://images.pokellector.com/cards/jp/Forbidden%20Light/108.jpg",
    "https://den-sys.com/pics/sm6-108.jpg",
    "https://www.serebii.net/card/sm6/108.jpg",
    "https://pkmncards.com/wp-content/uploads/sm6-108-eneporter-forbidden-light.jpg",
    "https://assets.pokemon.com/assets/cms2-jp/img/cards/web/SM6/SM6_JP_108.png",
]
for u in cands:
    try:
        r = c.get(u)
        print(r.status_code, len(r.content), u)
        if r.status_code == 200 and len(r.content) > 8000:
            OUT.joinpath("108-candidate.bin").write_bytes(r.content)
    except Exception as e:
        print("ERR", e, u)
