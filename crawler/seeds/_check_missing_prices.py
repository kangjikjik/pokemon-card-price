import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
from supabase import create_client
from lib.rarity_rank import is_displayable_rarity

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

for code in ["MG6", "MG5a"]:
    s = sb.table("card_sets").select("id,name_kr").eq("set_code", code).single().execute()
    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity,prices_kr(price_krw)")
        .eq("set_id", s.data["id"])
        .order("card_number")
        .execute()
        .data
        or []
    )
    hits = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    no_price = []
    for c in hits:
        pk = c.get("prices_kr") or []
        price = pk[-1]["price_krw"] if pk else 0
        if not price:
            no_price.append(c)
    print(f"=== {s.data['name_kr']}({code}) 시세 대상 {len(hits)}장, 없음 {len(no_price)} ===")
    for c in no_price:
        print(f"  {c['card_number']} {c['rarity']} {c['name_kr']}")
