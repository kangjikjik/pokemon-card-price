"""Patch remaining JP URLs + debug price extraction."""
from __future__ import annotations

import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
c = httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=20)

def prices(url: str):
    r = c.get(url)
    text = r.text
    pats = [
        r"希望小売価格[\]：:\s]*([\d,]+)\s*円",
        r"\[希望小売価格\]\s*([\d,]+)\s*円",
        r"希望小売価格[^\d]{0,40}([\d,]+)\s*円",
        r"([\d,]+)円（税込）",
    ]
    found = []
    for p in pats:
        found += [int(x.replace(",", "")) for x in re.findall(p, text)]
    packish = [y for y in found if 100 <= y <= 600]
    print(url, r.status_code, "all", found[:15], "packish", packish[:10])

for u in [
    "https://www.pokemon-card.com/ex/s12a/",
    "https://www.pokemon-card.com/ex/s12/",
    "https://www.pokemon-card.com/ex/s10b/",
    "https://www.pokemon-card.com/ex/sm12a/",
    "https://www.pokemon-card.com/ex/sm8b/",
    "https://www.pokemon-card.com/ex/s10a/",
    "https://www.pokemon-card.com/products/s/s1a.html",
    "https://www.pokemon-card.com/products/s/s6a.html",
    "https://www.pokemon-card.com/products/s/s5.html",
    "https://www.pokemon-card.com/products/s/s6.html",
    "https://www.pokemon-card.com/products/s/s7.html",
    "https://www.pokemon-card.com/products/s/s8a.html",
    "https://www.pokemon-card.com/products/s/s9a.html",
]:
    prices(u)
