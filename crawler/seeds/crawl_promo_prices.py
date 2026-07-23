"""
프로모(P) 카드 시세 수집 — 증정·이벤트·Black Star 등.

  python crawl_promo_prices.py --apply
  python crawl_promo_prices.py --set PRM-SV --apply
  python crawl_promo_prices.py --apply --missing-only
"""
from __future__ import annotations

import os
import sys
from time import sleep

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

import httpx  # noqa: E402

from lib.collectory_prices import (  # noqa: E402
    CollectoryPriceIndex,
    fetch_set_kr_prices,
    lookup_collectory_card_id,
)
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.rarity_rank import is_promo_rarity  # noqa: E402
from promo_catalog import PROMO_BY_CODE, PROMO_SET_CODES  # noqa: E402
from crawl_set_prices import (  # noqa: E402
    APPLY,
    FAST,
    HEADERS,
    MISSING_ONLY,
    QUIET,
    _log,
    _prefetch_bunjang,
    crawl_card,
    get_arg,
    resolve_collectory_price,
    _has_bunjang_listing,
)
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()


def promo_set_codes() -> list[str]:
    single = get_arg("--set", "").upper()
    if single:
        return [single]
    return list(PROMO_SET_CODES)


def load_promo_cards(set_code: str) -> tuple[int, str, list[dict]]:
    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).single().execute().data
    set_id = row["id"]
    set_name = row["name_kr"] or set_code
    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity")
        .eq("set_id", set_id)
        .order("card_number")
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_promo_rarity(c.get("rarity"))]
    if MISSING_ONLY:
        priced = (
            sb.table("prices_kr")
            .select("card_id")
            .in_("card_id", [c["id"] for c in cards])
            .gt("price_krw", 0)
            .execute()
            .data
            or []
        )
        priced_ids = {r["card_id"] for r in priced}
        cards = [c for c in cards if c["id"] not in priced_ids]
    return set_id, set_name, cards


def lookup_promo_collectory_id(
    index: CollectoryPriceIndex,
    card_number: str,
    name_kr: str,
) -> str:
    for rar in ("P", "PROMO"):
        cid = lookup_collectory_card_id(index, card_number, name_kr, rar)
        if cid:
            return cid
    return ""


def crawl_promo_set(set_code: str) -> int:
    meta = PROMO_BY_CODE.get(set_code)
    if not meta:
        print(f"unknown promo set: {set_code}")
        return 1

    set_id, set_name, cards = load_promo_cards(set_code)
    print(f"\n=== {set_name}({set_code}) 프로모 시세 ===")
    print(f"대상: {len(cards)}장")
    if not cards:
        return 0

    col_client: httpx.Client | None = None
    col_prices: CollectoryPriceIndex | None = None
    quote_cache: dict = {}

    if meta.collectory_id:
        col_client = httpx.Client(timeout=30, headers=HEADERS)
        col_prices = fetch_set_kr_prices(meta.collectory_id, client=col_client)
        card_ids = []
        for card in cards:
            cid = lookup_promo_collectory_id(
                col_prices, card.get("card_number") or "", card["name_kr"] or ""
            )
            if cid:
                card_ids.append(cid)
        if card_ids:
            from lib.collectory_public import preload_public_quotes

            quote_cache = preload_public_quotes(card_ids, col_client, workers=16)

    bunjang_cache: dict[int, list[int]] = {}
    if FAST and col_prices is not None:
        need_bj = []
        for card in cards:
            sold, listings, _, listing_src = resolve_collectory_price(
                card,
                col_prices,
                col_client,
                set_code=set_code,
                set_name_kr=set_name,
                quote_cache=quote_cache,
                use_auth_api=False,
            )
            if not sold and not _has_bunjang_listing(listing_src):
                need_bj.append(card)
        if need_bj:
            bunjang_cache = _prefetch_bunjang(
                cards=need_bj, set_name_kr=set_name, set_code=set_code, fast=True
            )

    ok = 0
    priced_rows: list[dict] = []
    try:
        for card in cards:
            _log(f"\n[{card['card_number']}] {card['name_kr']} (P)")
            median, low, n, source = crawl_card(
                card,
                set_name,
                set_code,
                col_prices,
                col_client,
                fast=FAST,
                quote_cache=quote_cache,
                use_auth_api=not FAST,
                bunjang_cache=bunjang_cache if FAST else None,
            )
            if n > 0:
                _log(f"  => {median:,}원 / 최저 {low:,}원 ({n}건, {source})")
            else:
                _log("  => 미등록")

            if APPLY and median > 0:
                priced_rows.append(
                    {"card_id": card["id"], "price_krw": median, "source": source}
                )
                ok += 1
            if not FAST:
                sleep(0.5)
    finally:
        if col_client:
            col_client.close()

    if APPLY and cards:
        all_ids = [c["id"] for c in cards]
        save_daily_snapshots(sb, "prices_kr", all_ids, priced_rows)
        print(f"\n{set_code} 완료: {ok}/{len(cards)}장 시세 저장")
    return 0


def main() -> None:
    codes = promo_set_codes()
    failed = 0
    for code in codes:
        if crawl_promo_set(code) != 0:
            failed += 1
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
