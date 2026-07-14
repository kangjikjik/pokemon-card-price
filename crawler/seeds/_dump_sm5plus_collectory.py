"""Dump collectory rarities for SM5+ and peek nearby SM sets for HR/UR gaps."""
from __future__ import annotations

import os
import sys
from collections import Counter

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from collectory_map import COLLECTORY_API
from kr_sets import KR_SETS
from seed_from_collectory import parse_rarity, resolve_rarity

client = httpx.Client(timeout=90, follow_redirects=True)


def dump(code: str, cid: str) -> None:
    r = client.get(f"{COLLECTORY_API}/cards", params={"set_id": cid, "limit": 500})
    cards = r.json().get("data") or r.json() or []
    if isinstance(cards, dict):
        cards = cards.get("data") or []
    raw = Counter()
    resolved = Counter()
    high = []
    for c in cards:
        rar_raw = (c.get("rarity") or "").strip()
        raw[rar_raw] += 1
        rr = resolve_rarity(c, True)
        if rr:
            resolved[rr] += 1
        num = c.get("number") or c.get("card_number") or ""
        # secrets usually number > set size
        try:
            n = int(str(num).split("/")[0])
        except Exception:
            n = 0
        if n >= 95 or rar_raw in ("HR", "UR", "SR", "PR", "RR") or (rr and rr != "RR"):
            high.append((num, rar_raw, rr, c.get("name_ko") or c.get("name") or c.get("name_en")))
    print(f"\n=== {code} cards={len(cards)} raw={dict(raw)} resolved={dict(resolved)}")
    for row in sorted(high, key=lambda x: x[0] or ""):
        print(f"  {row[0]!s:12} raw={row[1]!s:6} -> {row[2]!s:4} {row[3]}")


for s in KR_SETS:
    if s.code in ("SM5+", "SM5", "SM6", "SM4"):
        dump(s.code, s.collectory_id)
