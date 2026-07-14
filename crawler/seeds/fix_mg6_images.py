"""MG6 시크릿 카드(082~118) image_url만 수정 — Playwright 불필요"""
import os
from dotenv import load_dotenv
from supabase import create_client

YUYU_FRONT = "https://card.yuyu-tei.jp/poc/front/m05/{page_id}.jpg"

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

set_row = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute()
set_id = set_row.data["id"]
cards = sb.table("cards").select("id,card_number,image_url,rarity,name_jp").eq("set_id", set_id).execute().data or []

updated = 0
for c in cards:
    num_str = c.get("card_number") or ""
    if not num_str or "/" not in num_str:
        continue
    card_num = int(num_str.split("/")[0])
    if card_num < 82:
        continue

    new_url = YUYU_FRONT.format(page_id=10000 + card_num)
    old_url = c.get("image_url") or ""
    if old_url == new_url:
        continue

    sb.table("cards").update({"image_url": new_url}).eq("id", c["id"]).execute()
    print(f"  {card_num:03d} {c['rarity']:4} {c['name_jp']:20} -> ...m05/{10000+card_num}.jpg")
    updated += 1

print(f"\n[완료] {updated}장 image_url 수정")
