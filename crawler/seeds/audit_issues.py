"""name_kr에 일본어 잔존·rarity_rank 불일치·이미지 누락 현황"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import FEATURED_SET_CODES
from lib.rarity_rank import rank_for_rarity

TARGET = list(FEATURED_SET_CODES)


def has_japanese(t: str) -> bool:
    return bool(re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", t or ""))


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = sb.table("card_sets").select("id,set_code").in_("set_code", TARGET).execute().data or []
    set_ids = [s["id"] for s in sets]

    cards = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,name_kr,name_jp,rarity,rarity_rank,image_url,set_id")
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

    bad_names = [c for c in cards if has_japanese(c.get("name_kr") or "")]
    wrong_rank = [
        c for c in cards
        if rank_for_rarity(c.get("rarity")) != (c.get("rarity_rank") or 0)
    ]
    no_img = sum(1 for c in cards if not c.get("image_url"))

    print(f"total featured cards: {len(cards)}")
    print(f"name_kr with Japanese: {len(bad_names)}")
    print(f"wrong rarity_rank: {len(wrong_rank)}")
    print(f"no image: {no_img}")

    if bad_names:
        print("\n=== bad name samples ===")
        for c in bad_names[:15]:
            print(f"  {c['name_kr']!r} (jp={c.get('name_jp')!r})")

    if wrong_rank:
        print("\n=== rarity rank mismatches ===")
        for r, n in Counter(c["rarity"] for c in wrong_rank).most_common():
            print(f"  {r}: {n}")


if __name__ == "__main__":
    main()
