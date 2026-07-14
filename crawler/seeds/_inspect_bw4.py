"""Inspect BW4 collectory payload thoroughly."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

from collectory_map import COLLECTORY_API
from kr_sets import KR_BY_CODE
from seed_from_collectory import parse_rarity, normalize_card_number

code = "BW4"
meta = KR_BY_CODE[code]
client = httpx.Client(timeout=90)
raw = client.get(f"{COLLECTORY_API}/sets/{meta.collectory_id}/cards").json().get("cards") or []
print("total", len(raw))
print("raw rarity", Counter((x.get("rarity") or "EMPTY") for x in raw))
print()
for card in sorted(raw, key=lambda x: x.get("card_number") or ""):
    pr = parse_rarity(card)
    num = card.get("card_number")
    name = card.get("name_ko") or card.get("name_kr") or card.get("name_en") or card.get("name")
    flag = "KEEP" if pr else "SKIP"
    print(f"{flag:4} parse={pr!s:5} raw={card.get('rarity')!s:8} num={num} name={name}")

# dump one sample with all keys
if raw:
    print("\nkeys:", sorted(raw[0].keys()))
    print(json.dumps(raw[0], ensure_ascii=False, indent=2)[:800])

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
set_row = sb.table("card_sets").select("id").eq("set_code", code).single().execute().data
db = sb.table("cards").select("id,card_number,rarity,name_kr,image_url").eq("set_id", set_row["id"]).execute().data or []
print("\nDB cards", len(db))
for r in db:
    print(f"  {r['rarity']:4} {r['card_number']} {r['name_kr']}")
