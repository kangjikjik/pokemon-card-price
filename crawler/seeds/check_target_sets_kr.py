"""10개 인기 세트 한글명 누락 현황"""
import os, re
from dotenv import load_dotenv
from supabase import create_client

TARGET_SETS = [
    "SV2a", "SV4a", "SV3a", "SV2D", "SV8a",
    "SV5a", "SV1S", "SV1V", "MG6", "MG4a", "SV7",
]

def has_hangul(t):
    return bool(re.search(r"[\uAC00-\uD7A3]", t or ""))

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

sets = sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", TARGET_SETS).execute().data or []
code_to_id = {s["set_code"]: s["id"] for s in sets}

print("=== 대상 세트 DB 존재 여부 ===")
for code in TARGET_SETS:
    sid = code_to_id.get(code)
    if not sid:
        print(f"  MISSING: {code}")
        continue
    cards = sb.table("cards").select("id,name_kr,name_jp,name_en").eq("set_id", sid).execute().data or []
    missing = [c for c in cards if not has_hangul(c.get("name_kr"))]
    print(f"  {code}: 총 {len(cards)}장, 한글명 없음 {len(missing)}장")
    for c in missing[:5]:
        print(f"    - {c.get('name_en') or c.get('name_jp')}")
