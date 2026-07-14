"""희귀도 이상치 간단 감사 — ACE 빈번호, C/U/R 과다 등"""
from __future__ import annotations

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# ACE remaining
ace = sb.table("cards").select("id,name_kr,card_number,set_id").eq("rarity", "ACE").execute().data or []
print(f"ACE remaining: {len(ace)}")
empty = [r for r in ace if not (r.get("card_number") or "").strip()]
print(f"ACE empty card_number: {len(empty)}")

# MG6 ACE check
sets = sb.table("card_sets").select("id,set_code").eq("set_code", "MG6").execute().data or []
if sets:
    mg6_id = sets[0]["id"]
    mg6_ace = [r for r in ace if r["set_id"] == mg6_id]
    print(f"MG6 ACE: {len(mg6_ace)}")

# rarity distribution sample
all_r = sb.table("cards").select("rarity").execute().data or []
print("rarity counts:", dict(Counter(r["rarity"] for r in all_r).most_common(25)))
