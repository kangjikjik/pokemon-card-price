"""대상 세트 카드 rarity_rank 일괄 정규화"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from lib.rarity_rank import rank_for_rarity

from kr_sets import FEATURED_SET_CODES

TARGET_SETS = list(FEATURED_SET_CODES)


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    sets = sb.table("card_sets").select("id,set_code").in_("set_code", TARGET_SETS).execute().data or []
    set_ids = [s["id"] for s in sets]

    cards = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,rarity,rarity_rank")
            .in_("set_id", set_ids)
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        cards.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    updated = 0
    for card in cards:
        expected = rank_for_rarity(card.get("rarity"))
        if card.get("rarity_rank") != expected:
            sb.table("cards").update({"rarity_rank": expected}).eq("id", card["id"]).execute()
            updated += 1

    print(f"[완료] {updated}/{len(cards)}장 rarity_rank 정규화")


if __name__ == "__main__":
    main()
