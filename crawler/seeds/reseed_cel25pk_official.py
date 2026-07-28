"""Reseed CEL25PK with the complete official 25-card checklist."""
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

# 공식 25종 및 번호:
# https://www.pokemon-card.com/ex/25th/s8aP/
# 한국 발매 확인:
# https://www.pokemonkorea.co.kr/news/2/10890
OFFICIAL_CARDS: list[tuple[str, str, str, str]] = [
    ("001/025", "리자몽", "リザードン", "Charizard"),
    ("002/025", "이상해꽃", "フシギバナ", "Venusaur"),
    ("003/025", "거북왕", "カメックス", "Blastoise"),
    ("004/025", "가짜 오박사", "にせオーキドはかせ", "Imposter Professor Oak"),
    ("005/025", "나쁜 갸라도스", "わるいギャラドス", "Dark Gyarados"),
    ("006/025", "로켓단 등장!", "ロケット団参上！", "Here Comes Team Rocket!"),
    ("007/025", "_____의 피카츄", "_____のピカチュウ", "_____’s Pikachu"),
    ("008/025", "R단의 썬더", "R団のサンダー", "Rocket's Zapdos"),
    ("009/025", "삐", "ピィ", "Cleffa"),
    ("010/025", "빛나는 잉어킹", "ひかるコイキング", "Shining Magikarp"),
    ("011/025", "마그마단의 그란돈", "マグマ団のグラードン", "Team Magma's Groudon"),
    ("012/025", "블래키", "ブラッキー☆", "Umbreon"),
    ("013/025", "로켓단의 간부", "ロケット団の幹部", "Rocket's Admin."),
    ("014/025", "뮤 ex", "ミュウex", "Mew ex"),
    ("015/025", "가디안 ex", "サーナイトex", "Gardevoir ex"),
    ("016/025", "점토도리", "ネンドール", "Claydol"),
    ("017/025", "렌트라 GL LV.X", "レントラーGL LV.X", "Luxray GL LV.X"),
    ("018/025", "한카리아스 C LV.X", "ガブリアスC LV.X", "Garchomp C LV.X"),
    ("019/025", "코리갑", "ドンファン", "Donphan"),
    ("020/025", "레시라무", "レシラム", "Reshiram"),
    ("021/025", "제크로무", "ゼクロム", "Zekrom"),
    ("022/025", "뮤츠 EX", "ミュウツーEX", "Mewtwo EX"),
    ("023/025", "제르네아스 EX", "ゼルネアスEX", "Xerneas EX"),
    ("024/025", "M 레쿠쟈 EX", "MレックウザEX", "M Rayquaza EX"),
    ("025/025", "카푸나비나 GX", "カプ・テテフGX", "Tapu Lele GX"),
]

# 이전 12장짜리 Collectory 시드의 번호가 공식 번호와 달랐다. 최초 교정 시
# 이 매핑으로 기존 카드 ID(및 연결된 가격 이력)를 올바른 카드에 보존한다.
LEGACY_TARGET_BY_NUMBER = {
    "001/025": "001/025",  # Charizard
    "002/025": "002/025",  # Venusaur
    "003/025": "003/025",  # Blastoise
    "004/025": "007/025",  # Birthday Pikachu
    "006/025": "012/025",  # Umbreon
    "007/025": "010/025",  # Shining Magikarp
    "008/025": "021/025",  # Zekrom
    "012/025": "005/025",  # Dark Gyarados
    "013/025": "022/025",  # Mewtwo EX
    "014/025": "024/025",  # M Rayquaza EX
    "015/025": "009/025",  # Cleffa
    "016/025": "015/025",  # Gardevoir ex
}


def gallery_url(card_number: str) -> str:
    number = int(card_number.split("/", 1)[0])
    return f"https://www.pokemon-card.com/ex/25th/assets/images/s8aP/card-{number}.png"


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

    db_cards = (
        sb.table("cards")
        .select("id,card_number")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    reusable_by_target = (
        {
            LEGACY_TARGET_BY_NUMBER[c["card_number"]]: c["id"]
            for c in db_cards
            if c["card_number"] in LEGACY_TARGET_BY_NUMBER
        }
        if len(db_cards) < len(OFFICIAL_CARDS)
        else {c["card_number"]: c["id"] for c in db_cards}
    )

    seen_ids: set[int] = set()
    for card_number, name_kr, name_jp, name_en in OFFICIAL_CARDS:
        image_url = gallery_url(card_number)
        payload = {
            "set_id": set_id,
            "card_number": card_number,
            "rarity": "P",
            "rarity_rank": rank_for_rarity("P"),
            "name_kr": name_kr,
            "name_jp": name_jp,
            "name_en": name_en,
            "image_url": image_url,
        }
        existing_id = reusable_by_target.get(card_number)
        if existing_id:
            sb.table("cards").update(payload).eq("id", existing_id).execute()
            seen_ids.add(existing_id)
        else:
            inserted = sb.table("cards").insert(payload).execute().data or []
            if inserted:
                seen_ids.add(inserted[0]["id"])
        print(f"  {card_number} {name_kr} -> {image_url}")

    for c in db_cards:
        if c["id"] not in seen_ids:
            delete_card(c["id"])
            print(f"  delete orphan {c['card_number']}")

    print("Done.")


if __name__ == "__main__":
    main()
