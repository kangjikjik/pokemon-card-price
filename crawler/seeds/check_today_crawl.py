"""오늘 크롤된 팩별 개수 확인."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from utils.db import get_supabase
from kr_sets import KR_SETS

load_dotenv()
sb = get_supabase()

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# 오늘 저장된 prices_kr 전체
total = sb.table("prices_kr").select("id", count="exact").gte("fetched_at", today + "T00:00:00Z").execute()
print(f"오늘({today}) 저장된 KR 카드 시세 총계: {total.count}건")

# pid가 있는 개별 거래 기록 (sold:bunjang:PID 형식)
pid_count = sb.table("prices_kr").select("id", count="exact").gte("fetched_at", today + "T00:00:00Z").like("source", "sold:bunjang:__%").execute()
print(f"  - 개별 PID 기록 (URL 링크 가능): {pid_count.count}건")

# 팩별 확인
print("\n팩별 오늘 크롤 현황:")
all_sets = sb.table("card_sets").select("id,set_code,name_kr").execute()
set_map = {s["id"]: (s["set_code"], s["name_kr"]) for s in all_sets.data}

for s in all_sets.data[:30]:
    set_id = s["id"]
    # 해당 팩의 카드 id 목록
    cards = sb.table("cards").select("id").eq("set_id", set_id).execute()
    card_ids = [c["id"] for c in cards.data]
    if not card_ids:
        continue
    cnt = sb.table("prices_kr").select("id", count="exact").in_("card_id", card_ids).gte("fetched_at", today + "T00:00:00Z").execute()
    if cnt.count and cnt.count > 0:
        pid_c = sb.table("prices_kr").select("id", count="exact").in_("card_id", card_ids).gte("fetched_at", today + "T00:00:00Z").like("source", "sold:bunjang:__%").execute()
        print(f"  {s['set_code']:6s} ({s['name_kr'][:8]:8s}): {cnt.count}건 (PID: {pid_c.count}건)")
