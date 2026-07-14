"""전 featured 세트: RR+ 카드 수 / 등급 종류 / collectory 대비 누락 전수."""
from __future__ import annotations

import os
import sys
from collections import Counter

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from collectory_map import COLLECTORY_API
from fill_oldest_rr_plus import RR_PLUS, expected_catalog, oldest_sets
from kr_sets import KR_SETS, KR_BY_CODE

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
client = httpx.Client(timeout=90, follow_redirects=True)

# 전체 featured (오래된순)
sets = sorted([s for s in KR_SETS if s.collectory_id], key=lambda s: (s.released_at, s.code))

print(f"{'code':8} {'name':18} db  exp miss grades")
print("-" * 70)
bad = []
for s in sets:
    rows = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data or []
    if not rows:
        print(f"{s.code:8} NO SET IN DB")
        bad.append((s.code, "no_set"))
        continue
    set_id = rows[0]["id"]
    cards = (
        sb.table("cards")
        .select("id,card_number,rarity,name_kr,image_url")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    rr = [c for c in cards if (c.get("rarity") or "") in RR_PLUS]
    grades = sorted({c.get("rarity") for c in rr})
    try:
        exp = expected_catalog(s.code, s.collectory_id, client)
    except Exception as e:
        print(f"{s.code:8} catalog ERR {e}")
        bad.append((s.code, "catalog_err"))
        continue
    db_keys = {(c.get("card_number") or "", c.get("rarity") or "") for c in rr}
    miss = [k for k in exp if k not in db_keys]
    flag = "!!" if miss or len(grades) <= 1 or len(rr) <= 2 else "OK"
    if flag == "!!":
        bad.append((s.code, f"db={len(rr)} exp={len(exp)} miss={len(miss)} grades={grades}"))
    print(
        f"{flag} {s.code:8} {s.name_kr[:18]:18} {len(rr):3} {len(exp):3} {len(miss):4} {grades}"
    )

print()
print(f"문제 세트 {len(bad)}/{len(sets)}")
for b in bad:
    print(" ", b)
