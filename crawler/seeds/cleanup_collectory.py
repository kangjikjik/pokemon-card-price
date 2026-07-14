"""featured 세트 중복·저가치·구 시드 카드 정리"""
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from collectory_map import COLLECTORY_API, COLLECTORY_SETS
from seed_from_collectory import parse_rarity, normalize_card_number, RARITY_OVERRIDES, SEED_SKIP

from kr_sets import FEATURED_SET_CODES

TARGET = [c for c in FEATURED_SET_CODES if c != "MG6"]
REMOVE_RARITIES = {"U", "C", "SA", "N", "CM", "UM", "PROMO"}


def delete_card(sb, card_id: int) -> None:
    sb.table("prices_kr").delete().eq("card_id", card_id).execute()
    sb.table("prices_jp").delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def expected_keys(set_code: str, collectory_id: str) -> set[tuple[str, str]]:
    cards = httpx.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards", timeout=90).json().get("cards") or []
    keys: set[tuple[str, str]] = set()
    for card in cards:
        rarity = parse_rarity(card)
        if not rarity:
            continue
        num = normalize_card_number(card.get("card_number") or "")
        if "CM" in (card.get("card_number") or ""):
            continue
        if (set_code, num) in SEED_SKIP:
            continue
        if (set_code, num) in RARITY_OVERRIDES:
            rarity = RARITY_OVERRIDES[(set_code, num)]
        if num:
            keys.add((num, rarity))
    return keys


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = sb.table("card_sets").select("id,set_code").in_("set_code", TARGET).execute().data or []

    removed = 0
    deduped = 0

    for s in sets:
        set_id = s["id"]
        code = s["set_code"]
        cfg = COLLECTORY_SETS[code]
        allowed = expected_keys(code, cfg["id"])

        cards = sb.table("cards").select("id,card_number,rarity,image_url,name_jp,name_kr").eq("set_id", set_id).execute().data or []

        # 1) 저가치 제거
        for c in cards:
            if c.get("rarity") in REMOVE_RARITIES:
                delete_card(sb, c["id"])
                removed += 1

        cards = [c for c in cards if c.get("rarity") not in REMOVE_RARITIES]

        # 2) (card_number, rarity) 중복 — collectory CDN 이미지 우선 유지
        groups: dict[tuple[str, str], list] = {}
        for c in cards:
            key = (c.get("card_number") or "", c.get("rarity") or "")
            if not key[0]:
                continue
            groups.setdefault(key, []).append(c)

        for key, group in groups.items():
            if len(group) <= 1:
                continue
            group.sort(key=lambda x: (
                0 if "cdn.collectory.cc" in (x.get("image_url") or "") else 1,
                0 if x.get("image_url") else 1,
                -x["id"],
            ))
            for extra in group[1:]:
                delete_card(sb, extra["id"])
                deduped += 1
                removed += 1

        # 3) collectory 기준 목록에 없는 카드 제거 (card_number 있는 경우)
        cards = sb.table("cards").select("id,card_number,rarity,image_url").eq("set_id", set_id).execute().data or []
        for c in cards:
            num = c.get("card_number") or ""
            if not num:
                continue
            key = (num, c.get("rarity") or "")
            if key not in allowed and "cdn.collectory.cc" not in (c.get("image_url") or ""):
                delete_card(sb, c["id"])
                removed += 1

        # 4) card_number 없는 구 시드 잔여 카드 제거
        cards = sb.table("cards").select("id,card_number").eq("set_id", set_id).execute().data or []
        for c in cards:
            if not c.get("card_number"):
                delete_card(sb, c["id"])
                removed += 1

        cnt = sb.table("cards").select("id", count="exact").eq("set_id", set_id).execute().count
        print(f"  {code}: {cnt} cards (allowed {len(allowed)})")

    print(f"\n[완료] removed={removed} deduped={deduped}")


if __name__ == "__main__":
    main()
