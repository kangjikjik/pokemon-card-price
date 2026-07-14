"""collectory 원본 vs DB RR 등급 교차 검증"""
import os
import re
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import FEATURED_SET_CODES, KR_BY_CODE
from collectory_map import COLLECTORY_API
from seed_from_collectory import parse_rarity, normalize_card_number, RARITY_SUFFIXES

RARITY_SUFFIX_RE = re.compile(
    r"(" + "|".join(re.escape(s) for s in sorted(RARITY_SUFFIXES, key=len, reverse=True)) + r"|R|U|C)$",
    re.I,
)


def rarity_from_number(raw_num: str) -> str | None:
    if "/" not in raw_num:
        return None
    suffix = raw_num.split("/")[-1].upper()
    for prefix in sorted(RARITY_SUFFIXES, key=len, reverse=True):
        if suffix.endswith(prefix):
            return prefix
    if suffix.endswith("M"):
        return None
    if re.match(r"^\d+R$", suffix):
        return "R"
    if re.match(r"^\d+RR$", suffix):
        return "RR"
    return None


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90)

    mismatches = []
    for code in FEATURED_SET_CODES:
        meta = KR_BY_CODE.get(code)
        if not meta or not meta.collectory_id:
            continue
        set_row = sb.table("card_sets").select("id").eq("set_code", code).single().execute().data
        if not set_row:
            continue
        set_id = set_row["id"]

        raw_cards = client.get(f"{COLLECTORY_API}/sets/{meta.collectory_id}/cards").json().get("cards") or []
        col_by_norm: dict[tuple[str, str], dict] = {}
        for card in raw_cards:
            exp = parse_rarity(card)
            if not exp:
                continue
            num = normalize_card_number(card.get("card_number") or "")
            col_by_norm[(num, exp)] = card

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
            db_r = db.get("rarity") or ""
            raw_match = None
            for card in raw_cards:
                if normalize_card_number(card.get("card_number") or "") == num:
                    raw_match = card
                    break
            raw_num = (raw_match or {}).get("card_number") or num
            from_num = rarity_from_number(raw_num.upper())

            col_r = parse_rarity(raw_match) if raw_match else None

            if db_r == "RR" and from_num == "R":
                mismatches.append((code, num, raw_num, db_r, from_num, col_r, db.get("name_kr")))
            elif db_r == "RR" and col_r == "R":
                mismatches.append((code, num, raw_num, db_r, from_num, col_r, db.get("name_kr")))
            elif db_r != col_r and col_r and db_r == "RR":
                mismatches.append((code, num, raw_num, db_r, from_num, col_r, db.get("name_kr")))

    print(f"mismatches: {len(mismatches)}")
    for m in mismatches[:40]:
        print(m)

    # also list any R rarity still in DB
    r_cards = sb.table("cards").select("id", count="exact").eq("rarity", "R").execute().count
    print(f"R rarity in DB: {r_cards}")


if __name__ == "__main__":
    main()
