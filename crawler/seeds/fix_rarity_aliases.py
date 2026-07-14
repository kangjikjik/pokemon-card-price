"""DB 레어도 표준화 (UR-ex→SR, IR→AR, R 제거)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from lib.rarity_rank import normalize_rarity, rank_for_rarity

from featured_sets import FEATURED_SET_CODES
REMOVE = {"U", "C", "SA", "N", "R", "CM", "UM", "PROMO", "M"}


def delete_card(sb, card_id: int) -> None:
    sb.table("prices_kr").delete().eq("card_id", card_id).execute()
    sb.table("prices_jp").delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = sb.table("card_sets").select("id").in_("set_code", FEATURED_SET_CODES).execute().data or []
    set_ids = [s["id"] for s in sets]

    cards = []
    offset = 0
    while True:
        batch = sb.table("cards").select("id,rarity,rarity_rank").in_("set_id", set_ids).range(offset, offset + 999).execute().data or []
        cards.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    updated = removed = 0
    for c in cards:
        if c["rarity"] in REMOVE:
            delete_card(sb, c["id"])
            removed += 1
            continue
        norm = normalize_rarity(c["rarity"])
        rank = rank_for_rarity(norm)
        if norm != c["rarity"] or rank != c["rarity_rank"]:
            sb.table("cards").update({"rarity": norm, "rarity_rank": rank}).eq("id", c["id"]).execute()
            updated += 1

    print(f"[완료] updated={updated} removed={removed}")


if __name__ == "__main__":
    main()
