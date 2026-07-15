"""RR vs AR price comparison for a set."""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

set_code = sys.argv[1] if len(sys.argv) > 1 else "MG6"
s = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).single().execute()
sid = s.data["id"]
name = s.data["name_kr"]

rows = (
    sb.table("cards")
    .select("card_number,name_kr,rarity,prices_kr(price_krw)")
    .eq("set_id", sid)
    .in_("rarity", ["RR", "AR"])
    .order("name_kr")
    .execute()
    .data
    or []
)

print(f"=== {name} ({set_code}) RR vs AR ===")
by_name: dict[str, dict[str, int]] = {}
for r in rows:
    p = r["prices_kr"][0]["price_krw"] if r.get("prices_kr") else 0
    key = r["name_kr"].replace(" ex", "").strip()
    by_name.setdefault(key, {})[r["rarity"]] = p
    print(f"{r['rarity']:3} {r['card_number']:8} {r['name_kr']:22} {p:>7,}원")

print("\n--- 같은 포켓몬 RR >= AR ---")
for key, prices in sorted(by_name.items()):
    rr = prices.get("RR", 0)
    ar = prices.get("AR", 0)
    if rr > 0 and ar > 0 and rr >= ar:
        print(f"  {key}: RR {rr:,} >= AR {ar:,}")
