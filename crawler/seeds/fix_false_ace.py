"""ACE 오표기 조사 + MG6 잘못된 ACE 삭제"""
from __future__ import annotations

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

rows = (
    sb.table("cards")
    .select("id,name_kr,name_jp,card_number,rarity,set_id")
    .eq("rarity", "ACE")
    .execute()
    .data
    or []
)
print(f"ACE total: {len(rows)}")

set_ids = list({r["set_id"] for r in rows})
sets = sb.table("card_sets").select("id,set_code,name_kr").in_("id", set_ids).execute().data or []
by_id = {s["id"]: s for s in sets}

print("by set:", dict(Counter(by_id.get(r["set_id"], {}).get("set_code", "?") for r in rows)))
for r in rows:
    s = by_id.get(r["set_id"], {})
    print(
        f"  {s.get('set_code','?'):6} #{(r.get('card_number') or ''):8} "
        f"{(r.get('name_kr') or r.get('name_jp') or '')}"
    )

# MG6 false ACE: empty card_number
mg6 = next((s for s in sets if s["set_code"] == "MG6"), None)
if mg6:
    false_ace = [
        r for r in rows
        if r["set_id"] == mg6["id"] and not (r.get("card_number") or "").strip()
    ]
    print(f"\nMG6 false ACE (empty number): {len(false_ace)}")
    for r in false_ace:
        print(f"  delete {r['id']} {r.get('name_kr')}")
    if false_ace:
        ids = [r["id"] for r in false_ace]
        sb.table("cards").delete().in_("id", ids).execute()
        print(f"deleted {len(ids)}")
else:
    print("MG6 set not found")
