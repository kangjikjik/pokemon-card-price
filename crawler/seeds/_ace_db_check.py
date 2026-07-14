"""ACE remaining check + DB image_url sync"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import KR_SETS

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

row = sb.table("card_sets").select("*").limit(1).execute().data
print("cols", list(row[0].keys()) if row else None)

synced = 0
for s in KR_SETS:
    if not s.box_image_kr:
        continue
    cur = sb.table("card_sets").select("id,image_url").eq("set_code", s.code).limit(1).execute().data
    if not cur:
        continue
    if cur[0].get("image_url") != s.box_image_kr:
        sb.table("card_sets").update({"image_url": s.box_image_kr}).eq("id", cur[0]["id"]).execute()
        synced += 1
        print(f"sync {s.code} -> {s.box_image_kr}")
print(f"synced {synced}")

ace = sb.table("cards").select("id,name_kr,card_number,set_id").eq("rarity", "ACE").execute().data or []
print(f"ACE count={len(ace)}")
false_ids = {3480, 3485, 3488, 3493, 3501, 3527, 3531}
print("false still", [a["id"] for a in ace if a["id"] in false_ids])
sets = sb.table("card_sets").select("id,set_code").in_("id", list({a["set_id"] for a in ace})).execute().data or []
by = {s["id"]: s["set_code"] for s in sets}
for a in sorted(ace, key=lambda x: (by.get(x["set_id"], ""), x.get("card_number") or "")):
    code = by.get(a["set_id"], "?")
    num = a.get("card_number") or ""
    print(f"  {code:6} #{num:10} {a.get('name_kr')}")
