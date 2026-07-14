"""세트별 카드명·등급 샘플 출력"""
import os, re
from dotenv import load_dotenv
from supabase import create_client

TARGET = ["SV2a", "SV4a", "SV3a", "SV2D", "SV8a", "SV5a", "SV1S", "SV1V", "MG6", "MG4a", "SV7"]

def has_hangul(t):
    return bool(re.search(r"[\uAC00-\uD7A3]", t or ""))
def has_japanese(t):
    return bool(re.search(r"[\u3040-\u30FF]", t or ""))

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
sets = sb.table("card_sets").select("id,set_code").in_("set_code", TARGET).execute().data or []

for s in sets:
    if s["set_code"] == "MG6":
        continue
    cards = sb.table("cards").select("name_kr,name_jp,rarity,rarity_rank,image_url").eq("set_id", s["id"]).order("rarity_rank", desc=True).limit(8).execute().data or []
    print(f"\n=== {s['set_code']} (top 8 by rarity_rank) ===")
    for c in cards:
        kr = c.get("name_kr") or ""
        jp = c.get("name_jp") or ""
        jp_in_kr = has_japanese(kr)
        print(f"  [{c['rarity']} rank={c['rarity_rank']}] kr={kr!r} jp_in_kr={jp_in_kr} img={'Y' if c.get('image_url') else 'N'}")
