"""일본어 잔존 name_kr 강제 재번역"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from supabase import create_client
from seeds.update_kr_from_jp import fetch_pokemon_names, fetch_en_to_kr, translate_name, has_japanese, TRAINER_JP_KR

from kr_sets import FEATURED_SET_CODES

TARGET = list(FEATURED_SET_CODES)

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
jp_kr = fetch_pokemon_names()
en_kr = fetch_en_to_kr()

sets = sb.table("card_sets").select("id").in_("set_code", TARGET).execute().data or []
set_ids = [s["id"] for s in sets]

cards = sb.table("cards").select("id,name_kr,name_jp").in_("set_id", set_ids).execute().data or []
fixed = 0
for c in cards:
    kr = c.get("name_kr") or ""
    jp = c.get("name_jp") or ""
    if not has_japanese(kr):
        continue
    # 전체 일본어명 직접 매핑 우선
    if jp in TRAINER_JP_KR:
        new_kr = TRAINER_JP_KR[jp]
    else:
        new_kr = translate_name(jp, jp_kr)
    if new_kr and not has_japanese(new_kr):
        sb.table("cards").update({"name_kr": new_kr}).eq("id", c["id"]).execute()
        fixed += 1
        print(f"FIXED: {kr} -> {new_kr}")
    else:
        print(f"STILL BAD: kr={kr} jp={jp} try={new_kr}")

print(f"fixed {fixed}")
