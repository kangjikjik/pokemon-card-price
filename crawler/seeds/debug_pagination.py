import os
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# default limit test
r1 = sb.table("cards").select("id", count="exact").execute()
print(f"total cards: {r1.count}")

r2 = sb.table("cards").select("id,name_jp").execute()
print(f"default query rows: {len(r2.data)}")

sid = sb.table("card_sets").select("id").eq("set_code","SV2a").single().execute().data["id"]
in_batch = [c for c in r2.data if False]  # can't filter without set_id in select

# paginated fetch
all_ids = []
offset = 0
while True:
    batch = sb.table("cards").select("id,set_id").range(offset, offset+999).execute().data or []
    if not batch:
        break
    all_ids.extend(batch)
    offset += 1000
    if len(batch) < 1000:
        break

sv2a_in_first_1000 = sb.table("cards").select("id").eq("set_id", sid).limit(1).execute()
first_page = sb.table("cards").select("id,set_id").range(0,999).execute().data
sv2a_count_first = sum(1 for c in first_page if c["set_id"]==sid)
print(f"SV2a cards in first 1000 rows: {sv2a_count_first}")
