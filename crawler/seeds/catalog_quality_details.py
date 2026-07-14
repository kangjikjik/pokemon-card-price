"""Catalog quality detail audit: missing card images and MG6 RR+ key diffs."""
from __future__ import annotations

import os
import sys
from collections import Counter

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from fill_oldest_rr_plus import RR_PLUS, expected_catalog  # noqa: E402
from kr_sets import KR_BY_CODE, KR_SETS  # noqa: E402
from seed_from_collectory import normalize_card_number  # noqa: E402


def norm_key(num: str, rar: str) -> tuple[str, str]:
    n = normalize_card_number(num or "")
    if "/" in n:
        left, right = n.split("/", 1)
        if left.isdigit():
            left = left.zfill(3)
        n = f"{left}/{right}"
    return (n, rar or "")


def fetch_all_cards(sb, set_ids: list[int]) -> list[dict]:
    cards: list[dict] = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,set_id,card_number,name_kr,name_jp,name_en,rarity,rarity_rank,image_url")
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
    return cards


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    set_rows = sb.table("card_sets").select("id,set_code,name_kr").execute().data or []
    by_id = {r["id"]: r for r in set_rows}
    featured_codes = {s.code for s in KR_SETS}
    featured_ids = [r["id"] for r in set_rows if r.get("set_code") in featured_codes]
    cards = fetch_all_cards(sb, featured_ids)

    no_img = [c for c in cards if not (c.get("image_url") or "").strip()]
    print(f"NO_IMAGE total={len(no_img)}")
    for c in sorted(no_img, key=lambda x: (by_id[x["set_id"]]["set_code"], x.get("card_number") or "")):
        s = by_id[c["set_id"]]
        print(
            f"  {s['set_code']:7} {c.get('card_number') or '-':9} {c.get('rarity') or '-':4} "
            f"{c.get('name_kr') or c.get('name_jp') or c.get('name_en') or ''}"
        )
    print("NO_IMAGE_BY_SET", dict(Counter(by_id[c["set_id"]]["set_code"] for c in no_img)))

    s = KR_BY_CODE["MG6"]
    set_id = next(r["id"] for r in set_rows if r.get("set_code") == "MG6")
    db_cards = sb.table("cards").select("card_number,rarity,name_kr,name_jp,image_url").eq("set_id", set_id).execute().data or []
    db_rr = [c for c in db_cards if (c.get("rarity") or "") in RR_PLUS]
    db_keys = {norm_key(c.get("card_number") or "", c.get("rarity") or "") for c in db_rr}
    client = httpx.Client(timeout=90, follow_redirects=True)
    exp = expected_catalog(s.code, s.collectory_id, client)
    exp_norm = {norm_key(k[0], k[1]): v for k, v in exp.items()}
    miss = [k for k in exp_norm if k not in db_keys]
    extra = [k for k in db_keys if k not in exp_norm]
    print(f"\nMG6_RRPLUS db={len(db_rr)} exp={len(exp)} miss={len(miss)} extra={len(extra)}")
    print("MG6 missing expected:")
    for num, rar in sorted(miss):
        card = exp_norm[(num, rar)]
        print(f"  MISS {num:9} {rar:4} {card.get('name_ko') or card.get('name') or card.get('name_en') or ''}")
    print("MG6 extra db:")
    db_by_key = {(c.get("card_number") or "", c.get("rarity") or ""): c for c in db_rr}
    for num, rar in sorted(extra):
        card = db_by_key[(num, rar)]
        print(f"  EXTRA {num:9} {rar:4} {card.get('name_kr') or card.get('name_jp') or card.get('name_en') or ''}")


if __name__ == "__main__":
    main()
