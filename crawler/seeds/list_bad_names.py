import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from supabase import create_client

TARGET = ["SV2a", "SV4a", "SV3a", "SV2D", "SV8a", "SV5a", "SV1S", "SV1V", "MG6", "MG4a", "SV7"]
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
sets = sb.table("card_sets").select("id").in_("set_code", TARGET).execute().data or []
ids = [s["id"] for s in sets]
cards = sb.table("cards").select("id,name_kr,name_jp").in_("set_id", ids).execute().data or []
bad = [c for c in cards if re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", c.get("name_kr") or "")]
for c in bad:
    print(f"{c['id']}|{c['name_kr']}|{c.get('name_jp')}")
