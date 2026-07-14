"""collectory 마스터볼 미러(M) 등급 카드 전체 삭제"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client


def delete_card(sb, card_id: int) -> None:
    sb.table("prices_kr").delete().eq("card_id", card_id).execute()
    sb.table("prices_jp").delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    cards = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,rarity")
            .eq("rarity", "M")
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        cards.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    for c in cards:
        delete_card(sb, c["id"])

    print(f"[완료] M등급 {len(cards)}장 삭제")


if __name__ == "__main__":
    main()
