"""featured 25 세트 카드·이미지 검증"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import FEATURED_SET_CODES, KR_BY_CODE

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

total = 0
print(f"{'code':5} | {'cards':>5} | {'img':5} | name")
print("-" * 50)
for code in FEATURED_SET_CODES:
    meta = KR_BY_CODE[code]
    row = sb.table("card_sets").select("id,image_url,name_kr").eq("set_code", code).single().execute().data
    cnt = sb.table("cards").select("id", count="exact").eq("set_id", row["id"]).execute().count
    img_ok = "pokemonkorea" in (row.get("image_url") or "")
    total += cnt
    print(f"{code:5} | {cnt:5} | {str(img_ok):5} | {row['name_kr']}")
print("-" * 50)
print(f"TOTAL: {total}")
