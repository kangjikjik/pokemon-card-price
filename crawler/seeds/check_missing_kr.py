"""한글명 없는 카드 확인"""
import os, re
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def has_hangul(t):
    return bool(re.search(r"[\uAC00-\uD7A3]", t or ""))

cards = sb.table("cards").select("id,name_kr,name_jp,name_en,set_id,card_sets(set_code)").execute().data or []
missing = [c for c in cards if not has_hangul(c.get("name_kr"))]
print(f"한글명 없음: {len(missing)} / {len(cards)}")
for c in missing[:40]:
    s = c.get("card_sets") or {}
    print(f"  [{s.get('set_code','?')}] {c.get('name_en') or c.get('name_jp')}")
