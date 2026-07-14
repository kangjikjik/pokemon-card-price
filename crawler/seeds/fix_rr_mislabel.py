"""RR로 잘못 등록된 R·RM 카드 제거 + SV3 박스 이미지 갱신"""
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import FEATURED_SET_CODES, KR_BY_CODE
from collectory_map import COLLECTORY_API
from seed_from_collectory import parse_rarity, normalize_card_number

SV3_BOX = "https://data1.pokemonkorea.co.kr/2023/08/2023-08-17_16-12-59-33370-1692256379.png"


def delete_card(sb, card_id: int) -> None:
    sb.table("prices_kr").delete().eq("card_id", card_id).execute()
    sb.table("prices_jp").delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90)

    sv3 = sb.table("card_sets").select("id").eq("set_code", "SV3").single().execute().data
    if sv3:
        sb.table("card_sets").update({"image_url": SV3_BOX}).eq("id", sv3["id"]).execute()
        print("SV3 image updated")

    removed = 0
    fixed = 0

    for code in FEATURED_SET_CODES:
        meta = KR_BY_CODE.get(code)
        if not meta or not meta.collectory_id:
            continue
        set_row = sb.table("card_sets").select("id").eq("set_code", code).single().execute().data
        if not set_row:
            continue
        set_id = set_row["id"]

        raw_cards = client.get(f"{COLLECTORY_API}/sets/{meta.collectory_id}/cards").json().get("cards") or []

        # norm → 허용 등급 집합 (collectory parse 기준)
        allowed: dict[str, set[str]] = {}
        r_only_norms: set[str] = set()
        for card in raw_cards:
            raw_num = (card.get("card_number") or "").upper()
            norm = normalize_card_number(card.get("card_number") or "")
            exp = parse_rarity(card)
            if exp:
                allowed.setdefault(norm, set()).add(exp)
            if raw_num.endswith("R") and not raw_num.endswith("RR") and not raw_num.endswith("RM"):
                if (card.get("rarity") or "").strip() in ("R", "r"):
                    r_only_norms.add(norm)

        db_cards = (
            sb.table("cards")
            .select("id,rarity,card_number,name_kr")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )

        for db in db_cards:
            num = db.get("card_number") or ""
            norm = normalize_card_number(num)
            db_r = db.get("rarity") or ""

            if norm in r_only_norms and db_r == "RR":
                delete_card(sb, db["id"])
                removed += 1
                print(f"  REMOVE {code} {num} {db.get('name_kr')} (R holo mislabeled RR)")
                continue

            exp_set = allowed.get(norm, set())
            if db_r and exp_set and db_r not in exp_set:
                if len(exp_set) == 1:
                    new_r = next(iter(exp_set))
                    from lib.rarity_rank import rank_for_rarity
                    sb.table("cards").update({
                        "rarity": new_r,
                        "rarity_rank": rank_for_rarity(new_r),
                    }).eq("id", db["id"]).execute()
                    fixed += 1
                    print(f"  FIX {code} {num} {db_r} -> {new_r}")
                elif db_r == "RR" and "RR" not in exp_set:
                    delete_card(sb, db["id"])
                    removed += 1
                    print(f"  REMOVE {code} {num} {db.get('name_kr')} (not in allowed {exp_set})")

    print(f"\n[완료] removed={removed} fixed={fixed}")


if __name__ == "__main__":
    main()
