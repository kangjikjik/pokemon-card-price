import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
s = sb.table("card_sets").select("*").eq("set_code", "MG6").execute()
print("MG6:", s.data)
if s.data:
    sid = s.data[0]["id"]
    cards = sb.table("cards").select("id,name_kr,name_jp,rarity,image_url").eq("set_id", sid).execute()
    print(f"cards: {len(cards.data)}")
    for c in cards.data:
        print(c["rarity"], c.get("name_kr") or "-", "|", c.get("name_jp"))
