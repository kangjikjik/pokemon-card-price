"""Inspect SM5+ cards in DB."""
from __future__ import annotations

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

rows = sb.table("card_sets").select("id,set_code,name_kr").eq("set_code", "SM5+").execute().data or []
print("set", rows)
sid = rows[0]["id"]
cards = (
    sb.table("cards")
    .select("card_number,name_kr,rarity,rarity_rank")
    .eq("set_id", sid)
    .order("rarity_rank", desc=True)
    .execute()
    .data
    or []
)
print("count", len(cards))
print(Counter(c["rarity"] for c in cards))
for c in cards:
    print(f"{c['card_number']:8} {c['rarity']:4} {c['name_kr']}")
