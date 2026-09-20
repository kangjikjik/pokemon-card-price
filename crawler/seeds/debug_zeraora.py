"""어비스아이 제라오라 SAR 거래 데이터 확인."""
import datetime
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from utils.db import get_supabase

load_dotenv()
sb = get_supabase()

# 어비스아이(MG6) set_id = 86
cards = sb.table("cards").select("id,name_kr,rarity,card_number").eq("set_id", 86).ilike("name_kr", "%제라오라%").execute()
print("제라오라 카드:", cards.data)

for card in cards.data:
    cid = card["id"]
    rows = sb.table("prices_kr").select("price_krw,source,fetched_at").eq("card_id", cid).gt("price_krw", 0).order("fetched_at", desc=True).limit(10).execute()
    print(f"\n[{card['card_number']}] {card['name_kr']} ({card['rarity']})")
    for r in rows.data:
        src = r["source"] or ""
        parts = src.split(":")
        ts_str = ""
        if len(parts) >= 4 and parts[1] == "bunjang":
            try:
                ts = int(parts[3])
                dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone(datetime.timedelta(hours=9)))
                ts_str = f" → 거래날짜(KST): {dt.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                ts_str = " → ts파싱실패"
        print(f"  {r['price_krw']:,}원 | fetched_at={r['fetched_at'][:16]} | source={src[:60]}{ts_str}")
