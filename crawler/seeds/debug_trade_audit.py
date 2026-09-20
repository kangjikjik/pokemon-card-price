"""거래내역 오류 감사 — SNKRDUNK 등급 오염, MUR 누락."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

import httpx
from dotenv import load_dotenv

from lib.collectory_jp import build_jp_card_id_map
from lib.collectory_public import preload_public_quotes_jp
from lib.price_resolve import is_graded_grade, classify_collectory_row_jp
from lib.snkrdunk_card_price import snkrdunk_sold_items_from_quotes
from lib.price_search import filter_prices_by_rarity_band
from utils.db import get_supabase

load_dotenv()
sb = get_supabase()


def audit_card(card_id: int, label: str = "") -> None:
    card = sb.table("cards").select("id,name_jp,name_kr,rarity,card_number,set_id").eq("id", card_id).single().execute().data
    print(f"\n=== {label or card_id} [{card['card_number']}] {card.get('name_jp') or card.get('name_kr')} ({card['rarity']}) ===")

    jp_rows = (
        sb.table("prices_jp")
        .select("price_krw,source")
        .eq("card_id", card_id)
        .like("source", "sold:%")
        .order("fetched_at", desc=True)
        .limit(15)
        .execute()
        .data
        or []
    )
    print(f"DB sold rows: {len(jp_rows)}")
    for r in jp_rows[:12]:
        print(f"  {r['price_krw']:,} | {r['source'][:65]}")

    client = httpx.Client(timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    col_map = build_jp_card_id_map([card], client, workers=2)
    col_id = col_map.get(card_id)
    print(f"collectory_id: {col_id}")
    if not col_id:
        client.close()
        return

    quotes = preload_public_quotes_jp([col_id], client, workers=2).get(col_id, [])
    snk_all = [q for q in quotes if q.source == "snkrdunk" and q.tier == "sold"]
    print(f"Collectory SNKRDUNK sold (parsed): {len(snk_all)}")
    for q in snk_all:
        print(f"  {q.price_krw:,} | grade={q.title!r} | date={q.trade_date} | title={q.title[:100] if q.title else ''}")

    items = snkrdunk_sold_items_from_quotes(quotes)
    prices = [it["price"] for it in items]
    filtered = filter_prices_by_rarity_band(prices, card["rarity"])
    print(f"After rarity band: {len(filtered)}/{len(prices)} — {sorted(filtered, reverse=True)[:5]}")
    client.close()


def inspect_zeraora_outlier() -> None:
    cid = "95cbdbb8-0f6a-4455-9d79-95428501d641"
    client = httpx.Client(timeout=120)
    quotes = preload_public_quotes_jp([cid], client, workers=1)[cid]
    for q in quotes:
        if q.source == "snkrdunk" and q.tier == "sold" and q.price_krw >= 100000:
            print("\n=== OUTLIER 128800 ===")
            print("price", q.price_krw)
            print("title repr:", repr(q.title))
            print("trade_date", q.trade_date)
            # re-parse raw - need grade from collectory row
    client.close()


if __name__ == "__main__":
    # 제라오라 SAR
    audit_card(3957, "Zeraora SAR")
    # 메가다크라이 MUR
    mur = (
        sb.table("cards")
        .select("id")
        .eq("set_id", 86)
        .eq("rarity", "MUR")
        .ilike("name_jp", "%ダークライ%")
        .execute()
        .data
    )
    if mur:
        audit_card(mur[0]["id"], "Mega Darkrai MUR")
    inspect_zeraora_outlier()
