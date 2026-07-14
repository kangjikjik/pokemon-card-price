"""세트별 한글명·rarity_rank 현황"""
import os, re
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

TARGET = ["SV2a", "SV4a", "SV3a", "SV2D", "SV8a", "SV5a", "SV1S", "SV1V", "MG6", "MG4a", "SV7"]

def has_hangul(t):
    return bool(re.search(r"[\uAC00-\uD7A3]", t or ""))

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
sets = sb.table("card_sets").select("id,set_code").in_("set_code", TARGET).execute().data or []

for s in sets:
    cards = sb.table("cards").select("name_kr,name_jp,rarity,rarity_rank").eq("set_id", s["id"]).execute().data or []
    no_kr = [c for c in cards if not has_hangul(c.get("name_kr"))]
    ranks = defaultdict(list)
    for c in cards:
        ranks[c.get("rarity")].append(c.get("rarity_rank"))
    print(f"=== {s['set_code']} cards={len(cards)} no_kr={len(no_kr)} ===")
    for r in sorted(ranks.keys()):
        vals = sorted(set(ranks[r]))
        print(f"  {r}: ranks={vals}")
    for c in no_kr[:3]:
        print(f"  NO_KR sample: {c.get('name_jp')}")
