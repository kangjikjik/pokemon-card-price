from __future__ import annotations

import json
from pathlib import Path
import os

from dotenv import load_dotenv
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from utils.db import get_supabase
from kr_sets import KR_SETS
from lib.trainer_item_cards import is_trainer_or_item_card

sb = get_supabase()
out = []
for s in KR_SETS:
    if s.code.upper() == "MG7":
        continue
    row = sb.table("card_sets").select("id").eq("set_code", s.code).single().execute().data
    if not row:
        continue
    sid = row["id"]
    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,name_jp,rarity,image_url")
        .eq("set_id", sid)
        .execute()
        .data
        or []
    )
    for c in cards:
        if not is_trainer_or_item_card(s.code, c.get("card_number") or "", c.get("name_jp") or ""):
            continue
        cid = c["id"]
        prices = (
            sb.table("prices_kr")
            .select("price_krw,source")
            .eq("card_id", cid)
            .gt("price_krw", 0)
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not prices:
            img = c.get("image_url") or ""
            img_ok = "pokemonkorea" in img or "cards.image.pokemonkorea" in img
            out.append(
                {
                    "set": s.name_kr,
                    "card_number": c.get("card_number"),
                    "name_kr": c.get("name_kr"),
                    "image_url": img,
                    "image_ok": img_ok,
                    "card_id": cid,
                }
            )

p = Path("_audit_out/unpriced_trainers.json")
p.parent.mkdir(parents=True, exist_ok=True)
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("written", p, "count", len(out))

