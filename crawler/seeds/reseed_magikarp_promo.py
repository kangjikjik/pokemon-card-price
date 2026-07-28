"""Upsert the Korea-exclusive Pokémon MEGA Festa 2026 Magikarp promo."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import rank_for_rarity
from utils.db import get_supabase

load_dotenv()
sb = get_supabase()

CARD_NUMBER = "040/M-P"
IMAGE_URL = "https://cdn.collectory.cc/cards/kr/M-P/040_M-P.webp"


def main() -> None:
    set_rows = (
        sb.table("card_sets")
        .select("id")
        .eq("set_code", "PRM-MISC")
        .execute()
        .data
        or []
    )
    if not set_rows:
        raise RuntimeError("PRM-MISC set not found")

    set_id = set_rows[0]["id"]
    payload = {
        "set_id": set_id,
        "name_kr": "잉어킹",
        "name_jp": "コイキング",
        "name_en": "Magikarp",
        "rarity": "P",
        "rarity_rank": rank_for_rarity("P"),
        "card_number": CARD_NUMBER,
        "image_url": IMAGE_URL,
    }
    existing = (
        sb.table("cards")
        .select("id")
        .eq("set_id", set_id)
        .eq("name_kr", "잉어킹")
        .execute()
        .data
        or []
    )
    if existing:
        card_id = existing[0]["id"]
        sb.table("cards").update(payload).eq("id", card_id).execute()
        print(f"Updated card {card_id}: {CARD_NUMBER} 잉어킹")
    else:
        inserted = sb.table("cards").insert(payload).execute().data or []
        print(f"Inserted card {inserted[0]['id']}: {CARD_NUMBER} 잉어킹")


if __name__ == "__main__":
    main()
