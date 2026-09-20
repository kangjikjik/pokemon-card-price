#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import httpx

from lib.collectory_jp import build_jp_card_id_map
from lib.collectory_public import preload_public_quotes_jp
from lib.jp_set_prices import prefetch_bunjang_jp, resolve_jp_card_price
from utils.db import get_supabase


def main() -> None:
    sb = get_supabase()
    card_id = 5794
    row = (
        sb.table("cards")
        .select("id, card_number, name_kr, name_jp, rarity, set_id")
        .eq("id", card_id)
        .single()
        .execute()
        .data
    )
    card = {
        "id": row["id"],
        "card_number": row["card_number"],
        "name_jp": row["name_jp"],
        "name_kr": row["name_kr"],
        "rarity": row.get("rarity"),
    }
    set_row = (
        sb.table("card_sets")
        .select("set_code, name_kr")
        .eq("id", row["set_id"])
        .single()
        .execute()
        .data
    )
    set_code = set_row["set_code"]

    client = httpx.Client(timeout=30)
    id_map = build_jp_card_id_map([card], client)
    collectory_id = id_map.get(card_id)
    quotes = preload_public_quotes_jp([collectory_id], client, workers=4) if collectory_id else {}
    bunjang = prefetch_bunjang_jp([card], card["name_kr"], set_code, fast=False)
    median, _low, n, source, _jpy = resolve_jp_card_price(
        card,
        collectory_id=collectory_id or "",
        quote_cache=quotes,
        bunjang_cache=bunjang,
        rate=9.5,
        set_name_kr=set_row.get("name_kr") or "",
        set_code=set_code,
        fast=False,
    )

    jp_rows = (
        sb.table("prices_jp")
        .select("*")
        .eq("card_id", card_id)
        .order("fetched_at", desc=True)
        .limit(5)
        .execute()
        .data
        or []
    )

    raw_quotes = quotes.get(collectory_id) if collectory_id else []
    sold = [q for q in raw_quotes if q.tier == "sold"]
    listings = [q for q in raw_quotes if q.tier == "listing"]

    out = {
        "card": card,
        "set_code": set_code,
        "collectory_id": collectory_id,
        "resolved_krw": median,
        "resolved_count": n,
        "resolved_source": source,
        "bunjang_count": len(bunjang.get(card_id) or []),
        "bunjang_prices": bunjang.get(card_id) or [],
        "collectory_sold": [
            {"price_krw": q.price_krw, "source": q.source, "title": q.title}
            for q in sold[:15]
        ],
        "collectory_listings": [
            {"price_krw": q.price_krw, "source": q.source, "title": q.title}
            for q in listings[:15]
        ],
        "latest_db_jp": jp_rows,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    client.close()


if __name__ == "__main__":
    main()
