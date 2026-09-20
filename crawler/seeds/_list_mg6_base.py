"""List all MG6 cards 1-81."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv()
from utils.db import get_supabase
from lib.trainer_item_cards import card_number_int

sb = get_supabase()
sid = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute().data["id"]
cards = (
    sb.table("cards")
    .select("card_number,name_kr,name_jp,rarity")
    .eq("set_id", sid)
    .execute()
    .data
    or []
)
print("total", len(cards))
for c in sorted(cards, key=lambda x: card_number_int(x.get("card_number") or "") or 0):
    n = card_number_int(c.get("card_number") or "") or 0
    if n <= 81:
        print(
            f"{c.get('card_number'):8} {(c.get('rarity') or ''):4} "
            f"{(c.get('name_kr') or ''):22} {(c.get('name_jp') or '')}"
        )
