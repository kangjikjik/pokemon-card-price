"""Reseed CEL25PK — pokemon-card.com 공식 이미지 + 포켓몬코리아 팩 이미지."""
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

# pokemoncard.co.kr/card/387 · pokemonkorea 공식 프로모팩 단독 이미지
PACK_IMAGE = "https://data1.pokemonkorea.co.kr/2021/10/2021-10-15_18-19-47-44100-1634289587.png"

# Collectory KR 번호 + 공식 일본 갤러리(s8a-P card-N.png) 매핑
# 출처: https://www.pokemonkorea.co.kr/news/2/10890 · https://pokemoncard.co.kr/card/387
OFFICIAL_CARDS: list[tuple[str, str, str, int]] = [
    ("001/025", "리자몽", "Charizard", 1),
    ("002/025", "이상해꽃", "Venusaur", 2),
    ("003/025", "거북왕", "Blastoise", 3),
    ("004/025", "피카츄 (생일츄)", "Pikachu", 8),
    ("006/025", "블래키", "Umbreon", 12),
    ("007/025", "빛나는 잉어킹", "Shining Magikarp", 10),
    ("008/025", "제크로무", "Zekrom", 17),
    ("012/025", "나쁜 갸라도스", "Dark Gyarados", 5),
    ("013/025", "뮤 ex", "Mew ex", 14),
    ("014/025", "M 레쿠쟈 EX", "M Rayquaza EX", 24),
    ("015/025", "레시라무", "Reshiram", 16),
    ("016/025", "가디언 ex", "Gardevoir ex", 15),
]


def gallery_url(n: int) -> str:
    return f"https://www.pokemon-card.com/ex/25th/assets/images/s8aP/card-{n}.png"


def delete_card(card_id: int) -> None:
    sb.table("prices_kr").delete().eq("card_id", card_id).execute()
    sb.table("prices_jp").delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main() -> None:
    set_row = sb.table("card_sets").select("id").eq("set_code", "CEL25PK").execute().data
    if not set_row:
        print("CEL25PK not found")
        return
    set_id = set_row[0]["id"]

    sb.table("card_sets").update({
        "name_kr": "25주년 기념 프로모팩",
        "released_at": "2021-10-22",
        "image_url": PACK_IMAGE,
    }).eq("id", set_id).execute()

    seen: set[str] = set()
    for card_number, name_kr, name_en, gallery_n in OFFICIAL_CARDS:
        seen.add(card_number)
        image_url = gallery_url(gallery_n)
        payload = {
            "set_id": set_id,
            "card_number": card_number,
            "rarity": "P",
            "rarity_rank": rank_for_rarity("P"),
            "name_kr": name_kr,
            "name_jp": name_en,
            "name_en": name_en,
            "image_url": image_url,
        }
        existing = (
            sb.table("cards")
            .select("id")
            .eq("set_id", set_id)
            .eq("card_number", card_number)
            .execute()
            .data
            or []
        )
        if existing:
            sb.table("cards").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            sb.table("cards").insert(payload).execute()
        print(f"  {card_number} {name_kr} -> card-{gallery_n}.png")

    db_cards = sb.table("cards").select("id,card_number").eq("set_id", set_id).execute().data or []
    for c in db_cards:
        if c["card_number"] not in seen:
            delete_card(c["id"])
            print(f"  delete orphan {c['card_number']}")

    print("Done.")


if __name__ == "__main__":
    main()
