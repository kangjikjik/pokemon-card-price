"""Locate JP Sword/Shield product pages and pack images."""
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

# search product list
for path in [
    "/products/s/",
    "/products/",
    "/archive/products/s1.html",
    "/products/s/sword.html",
    "/products/2019/s1.html",
    "/products/2019/12/s1.html",
    "/products/2020/s1.html",
]:
    u = "https://www.pokemon-card.com" + path
    r = client.get(u)
    print(path, r.status_code, len(r.text), r.url)

# try info articles
for u in [
    "https://www.pokemon-card.com/products/s/S1.html",
    "https://www.pokemon-card.com/info/2019/11/1911s1.html",
    "https://www.pokemon-card.com/info/2019/12/1912s1.html",
]:
    r = client.get(u)
    print(u, r.status_code)

# bulbapedia / wikimedia
wiki = [
    "https://archives.bulbagarden.net/wiki/Sword_(TCG)",
    "https://archives.bulbagarden.net/wiki/File:Sword_Booster_JP.png",
    "https://archives.bulbagarden.net/wiki/File:Shield_Booster_JP.png",
    "https://archives.bulbagarden.net/wiki/File:Sword_%26_Shield_Sword_pack.png",
]
print("\n=== wiki ===")
for u in wiki:
    r = client.get(u)
    print(r.status_code, u)
    if r.status_code == 200:
        imgs = re.findall(r'src="([^"]+\.(?:png|jpg))"', r.text)
        for src in imgs[:15]:
            if src.startswith("//"):
                src = "https:" + src
            print(" ", src[:120])
