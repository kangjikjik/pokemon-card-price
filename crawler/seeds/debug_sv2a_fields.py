import os
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
sid = sb.table("card_sets").select("id").eq("set_code","SV2a").single().execute().data["id"]
cards = sb.table("cards").select("name_jp,name_en,name_kr").eq("set_id",sid).ilike("name_jp","%フシギ%").execute().data
print(cards)
cards2 = sb.table("cards").select("name_jp,name_en,name_kr").eq("set_id",sid).is_("name_kr","null").limit(3).execute().data
print("null kr:", cards2)
cards3 = sb.table("cards").select("name_jp,name_en,name_kr").eq("set_id",sid).eq("name_kr","").limit(3).execute().data
print("empty kr:", cards3)
