"""collectory 시드 결과 검증"""
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from lib.rarity_rank import rank_for_rarity
from collectory_map import COLLECTORY_API, COLLECTORY_SETS
from seed_from_collectory import parse_rarity, normalize_card_number, SKIP_RARITIES

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def expected_count(collectory_id: str) -> int:
    cards = httpx.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards", timeout=90).json().get("cards") or []
    seen = set()
    n = 0
    for c in cards:
        r = parse_rarity(c)
        if not r:
            continue
        num = normalize_card_number(c.get("card_number") or "")
        if "CM" in (c.get("card_number") or ""):
            continue
        key = (num, r)
        if key in seen:
            continue
        seen.add(key)
        n += 1
    return n


def main():
    ok = True
    print("set_code | expected | db | box_ok | status")
    print("-" * 55)
    for set_code, cfg in COLLECTORY_SETS.items():
        set_row = sb.table("card_sets").select("id,image_url").eq("set_code", set_code).single().execute().data
        if not set_row:
            print(f"{set_code} | - | - | - | NO SET")
            ok = False
            continue

        exp = expected_count(cfg["id"])
        db_count = sb.table("cards").select("id", count="exact").eq("set_id", set_row["id"]).execute().count
        box_ok = set_row.get("image_url") == cfg["box_image"]
        bad_rank = (
            sb.table("cards")
            .select("id", count="exact")
            .eq("set_id", set_row["id"])
            .neq("rarity_rank", 0)
            .execute()
        )
        # count cards where rarity_rank mismatches
        cards = sb.table("cards").select("rarity,rarity_rank").eq("set_id", set_row["id"]).execute().data or []
        rank_bad = sum(1 for c in cards if c["rarity_rank"] != rank_for_rarity(c["rarity"]))
        excluded = sum(1 for c in cards if c["rarity"] in SKIP_RARITIES)

        status = "OK" if db_count >= exp * 0.9 and box_ok and rank_bad == 0 and excluded == 0 else "WARN"
        if status != "OK":
            ok = False
        print(f"{set_code:6} | {exp:8} | {db_count:3} | {str(box_ok):5} | {status} (rank_bad={rank_bad}, excluded={excluded})")

    print("\n[결과]", "PASS" if ok else "NEEDS REVIEW")


if __name__ == "__main__":
    main()
