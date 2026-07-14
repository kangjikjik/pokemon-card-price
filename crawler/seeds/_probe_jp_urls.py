"""Probe alternate pokemon-card.com URLs for failed sets."""
from __future__ import annotations

import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
HEADERS = {"User-Agent": "Mozilla/5.0"}
JP_PACK_RE = re.compile(r"希望小売価格[：:\s]*([\d,]+)\s*円")

CODES = {
    "S12a": [
        "https://www.pokemon-card.com/ex/s12a/",
        "https://www.pokemon-card.com/products/s/s12a.html",
        "https://www.pokemon-card.com/products/s/S12a.html",
    ],
    "S12": [
        "https://www.pokemon-card.com/ex/s12/",
        "https://www.pokemon-card.com/products/s/s12.html",
    ],
    "S11a": [
        "https://www.pokemon-card.com/products/s/s11a.html",
        "https://www.pokemon-card.com/ex/s11a/",
    ],
    "S10b": [
        "https://www.pokemon-card.com/products/s/s10b.html",
        "https://www.pokemon-card.com/ex/s10b/",
        "https://www.pokemon-card.com/products/s/S10b.html",
    ],
    "S10a": [
        "https://www.pokemon-card.com/ex/s10a/",
        "https://www.pokemon-card.com/products/s/s10a.html",
        "https://www.pokemon-card.com/products/s/pokemon-go.html",
    ],
    "S9a": [
        "https://www.pokemon-card.com/ex/s9a/",
        "https://www.pokemon-card.com/products/s/s9a.html",
    ],
    "S8": [
        "https://www.pokemon-card.com/products/s/s8.html",
        "https://www.pokemon-card.com/ex/s8/",
    ],
    "S8a": [
        "https://www.pokemon-card.com/ex/s8a/",
        "https://www.pokemon-card.com/products/s/s8a.html",
    ],
    "S7F": [
        "https://www.pokemon-card.com/products/s/s7.html",
        "https://www.pokemon-card.com/ex/s7/",
        "https://www.pokemon-card.com/products/s/s7f.html",
    ],
    "S7R": [
        "https://www.pokemon-card.com/ex/s7/",
        "https://www.pokemon-card.com/products/s/s7r.html",
        "https://www.pokemon-card.com/products/s/s7.html",
    ],
    "S6H": [
        "https://www.pokemon-card.com/ex/s6a/",
        "https://www.pokemon-card.com/products/s/s6a.html",
        "https://www.pokemon-card.com/ex/s6/",
    ],
    "S6G": [
        "https://www.pokemon-card.com/ex/s6/",
        "https://www.pokemon-card.com/products/s/s6.html",
    ],
    "S5F": [
        "https://www.pokemon-card.com/ex/s5/",
        "https://www.pokemon-card.com/products/s/s5.html",
    ],
    "S1a": [
        "https://www.pokemon-card.com/ex/s1a/",
        "https://www.pokemon-card.com/products/s/s1a.html",
    ],
    "SV2a": ["https://www.pokemon-card.com/ex/sv2a/"],
    "SM6": [
        "https://www.pokemon-card.com/products/sm/sm6.html",
        "https://www.pokemon-card.com/ex/sm6/",
        "https://www.pokemon-card.com/products/sm/SM6.html",
    ],
    "SM4": [
        "https://www.pokemon-card.com/products/sm/sm4.html",
        "https://www.pokemon-card.com/ex/sm4/",
    ],
    "SM8b": [
        "https://www.pokemon-card.com/products/sm/sm8b.html",
        "https://www.pokemon-card.com/ex/sm8b/",
    ],
    "SM12a": [
        "https://www.pokemon-card.com/products/sm/sm12a.html",
        "https://www.pokemon-card.com/ex/sm12a/",
    ],
}

c = httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20)
for code, urls in CODES.items():
    for u in urls:
        r = c.get(u)
        found = [int(x.replace(",", "")) for x in JP_PACK_RE.findall(r.text)]
        packs = [y for y in found if 100 <= y <= 600]
        print(f"{code:6} {r.status_code} packs={packs[:5]} {u}")
