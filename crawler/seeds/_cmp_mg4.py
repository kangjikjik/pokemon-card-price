"""Compare Inferno X DB names vs official trainer names."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv()
from lib.pokemoncard_kr import fetch_set_trainers, goods_name_for_set
from lib.trainer_item_cards import card_number_int
from utils.db import get_supabase

sb = get_supabase()
sid = sb.table("card_sets").select("id").eq("set_code", "MG4").single().execute().data["id"]
cards = (
    sb.table("cards")
    .select("card_number,name_kr,name_jp,rarity,image_url")
    .eq("set_id", sid)
    .execute()
    .data
    or []
)
print("DB total", len(cards))
for c in sorted(cards, key=lambda x: card_number_int(x.get("card_number") or "") or 0):
    n = card_number_int(c.get("card_number") or "") or 0
    if n >= 60:
        print(
            f"  {c.get('card_number'):8} {(c.get('rarity') or ''):4} "
            f"{(c.get('name_kr') or ''):20} {(c.get('name_jp') or '')}"
        )

goods = goods_name_for_set("인페르노X")
offs = fetch_set_trainers(goods)
print("\nOFFICIAL", len(offs))
for o in offs:
    print(f"  {o.printed} {o.rarity:4} {o.kind:10} {o.name_kr} {o.image_url.split('/')[-1]}")
