import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from supabase import create_client

TARGET = ["SV2a", "SV4a", "SV3a", "SV2D", "SV8a", "SV5a", "SV1S", "SV1V", "MG6", "MG4a", "SV7"]

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
sets = sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", TARGET).execute().data or []
for s in sets:
    cnt = sb.table("cards").select("id", count="exact").eq("set_id", s["id"]).execute().count
    print(f"{s['set_code']}: {cnt} cards")
