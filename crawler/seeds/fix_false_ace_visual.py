"""시각적으로 ACE SPEC이 아닌 가짜 ACE 삭제 + 재시드 방지 목록 출력"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
OUT = Path(__file__).parent / "_audit_out"
false = json.loads((OUT / "ace_false.json").read_text(encoding="utf-8"))

print(f"false ACE to delete: {len(false)}")
for r in false:
    code = r.get("set_code") or r.get("set")
    num = r.get("card_number") or r.get("num")
    name = r.get("name_kr") or r.get("name")
    print(f"  id={r['id']} {code} #{num} {name}")

ids = [r["id"] for r in false]
if not ids:
    print("nothing to delete")
    raise SystemExit(0)

# FK cleanup
for table in ("prices_kr", "prices_jp"):
    sb.table(table).delete().in_("card_id", ids).execute()
sb.table("cards").delete().in_("id", ids).execute()
print(f"deleted {len(ids)}")

# verify remaining ACE
rows = sb.table("cards").select("id,name_kr,card_number,rarity,set_id").eq("rarity", "ACE").execute().data or []
print(f"ACE remaining: {len(rows)}")
