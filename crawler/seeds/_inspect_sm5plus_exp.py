"""SM5+ collectory expected RR+ vs DB."""
from __future__ import annotations

import os
import sys
from collections import Counter

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from fill_oldest_rr_plus import RR_PLUS, expected_catalog
from kr_sets import KR_BY_CODE

load_dotenv()
s = KR_BY_CODE["SM5+"]
client = httpx.Client(timeout=90, follow_redirects=True)
exp = expected_catalog(s.code, s.collectory_id, client)
print("expected", len(exp), Counter(v["rarity"] for v in exp.values()))
for (num, rar), v in sorted(exp.items(), key=lambda x: (-ord(x[0][1][0]) if x[0][1] else 0, x[0][0])):
    print(f"  {num:10} {rar:4} {v.get('name_kr') or v.get('name_en')}")

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
sid = sb.table("card_sets").select("id").eq("set_code", "SM5+").execute().data[0]["id"]
db = sb.table("cards").select("card_number,rarity,name_kr").eq("set_id", sid).execute().data or []
db_keys = {(c["card_number"], c["rarity"]) for c in db}
miss = [k for k in exp if k not in db_keys]
print("\nMISSING", len(miss))
for num, rar in miss:
    print(f"  {num} {rar} {exp[(num,rar)]}")
