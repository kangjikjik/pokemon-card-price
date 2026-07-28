"""
프로모(P) 카드 시세 수집 — 확장팩과 동일 정책 (KR: Collectory+번개, JP: 유유테이).

  python crawl_promo_prices.py --apply
  python crawl_promo_prices.py --set CEL25PK --apply
  python crawl_promo_prices.py --set CEL25PK --apply --region KR
  python crawl_promo_prices.py --apply --missing-only

일일 배치: KR/JP 확장팩 배치 끝에 --region KR|JP 로 자동 호출 (별도 promo 배치 없음).
"""
from __future__ import annotations

import os
import sys
from time import sleep

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.collectory_prices import (  # noqa: E402
    CollectoryPriceIndex,
    build_collectory_index_from_search,
    fetch_set_kr_prices,
)
from lib.collectory_public import preload_public_quotes  # noqa: E402
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.rarity_rank import is_promo_rarity  # noqa: E402
from lib.yuyutei_prices import (  # noqa: E402
    HEADERS as YUYU_HEADERS,
    card_numbers_match,
    fetch_set_listings,
)
from promo_catalog import PROMO_BY_CODE, PROMO_SET_CODES, PROMO_YUYU_VERS  # noqa: E402
from crawl_set_prices import (  # noqa: E402
    APPLY,
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
from crawl_set_prices_jp import get_exchange_rate  # noqa: E402
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
        .select("id,card_number,name_kr,name_jp,rarity")
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
    from lib.collectory_prices import card_num_key, name_variants

    for rar in ("P", "PROMO"):
        num_key = (*card_num_key(card_number), rar)
        cid = index.card_ids.get(num_key, "")
        if cid:
            return cid
    for rar in ("P", "PROMO"):
        for variant in name_variants(name_kr):
            cid = index.card_ids_by_name.get((variant, rar), "")
            if cid:
                return cid
    return ""


def enrich_collectory_index(
    index: CollectoryPriceIndex,
    cards: list[dict],
    client: httpx.Client,
) -> int:
    """카드번호 기준 collectory 검색으로 card_id 보강 (프로모 오매칭 방지)."""
    from lib.collectory_prices import search_collectory_card_id

    added = 0
    for card in cards:
        num = card.get("card_number") or ""
        name = card["name_kr"] or ""
        rarity = card.get("rarity") or "P"
        cid = search_collectory_card_id(name, num, rarity, client)
        if cid:
            index.add(num, name, rarity, 0, card_id=cid)
            added += 1
    return added


def cards_needing_bunjang(
    cards: list[dict],
    col_prices: CollectoryPriceIndex | None,
    col_client: httpx.Client | None,
    set_code: str,
    set_name: str,
    quote_cache: dict,
) -> list[dict]:
    if col_prices is None:
        return list(cards)
    need: list[dict] = []
    for card in cards:
        sold, _, _, listing_src = resolve_collectory_price(
            card,
            col_prices,
            col_client,
            set_code=set_code,
            set_name_kr=set_name,
            quote_cache=quote_cache,
            use_auth_api=False,
        )
        if not sold and not _has_bunjang_listing(listing_src):
            need.append(card)
    return need


def crawl_promo_kr(set_code: str, set_name: str, cards: list[dict], meta) -> int:
    if not cards:
        return 0

    promo_fast = "--fast" in sys.argv
    if not promo_fast:
        print("  모드: 정밀 (프로모 기본 — Collectory+번개 다중 검색)")

    col_client: httpx.Client | None = None
    col_prices: CollectoryPriceIndex | None = None
    quote_cache: dict = {}

    col_client = httpx.Client(
        timeout=30,
        headers=HEADERS,
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=24),
    )
    if meta.collectory_id:
        col_prices = fetch_set_kr_prices(meta.collectory_id, client=col_client)
        added = enrich_collectory_index(col_prices, cards, col_client)
        print(f"  collectory 세트+검색 card_id: {len(col_prices.card_ids)}건 (검색 보강 {added})")
    else:
        col_prices = build_collectory_index_from_search(cards, col_client)
        print(f"  collectory 검색 card_id: {len(col_prices.card_ids)}건")

    card_ids: list[str] = []
    for card in cards:
        cid = lookup_promo_collectory_id(
            col_prices, card.get("card_number") or "", card["name_kr"] or ""
        )
        if cid:
            card_ids.append(cid)
    if card_ids:
        quote_cache = preload_public_quotes(card_ids, col_client, workers=16)
        print(f"  collectory 거래내역 프리로드: {len(quote_cache)}장")

    bunjang_cache: dict[int, list[int]] = {}
    if not promo_fast:
        bunjang_cache = _prefetch_bunjang(
            cards=list(cards), set_name_kr=set_name, set_code=set_code, fast=False
        )
        print(f"  번개 보강: {len(cards)}장 조회 → {len(bunjang_cache)}건")

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
                fast=promo_fast,
                quote_cache=quote_cache,
                use_auth_api=not promo_fast,
                bunjang_cache=bunjang_cache if not promo_fast else None,
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
            if not promo_fast:
                sleep(0.5)
    finally:
        if col_client:
            col_client.close()

    if APPLY and cards:
        all_ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_kr", all_ids, priced_rows)
        print(f"\n{set_code} KR 완료: {ok}/{len(cards)}장 (오늘 교체 {deleted}→{inserted})")
    else:
        print(f"\n{set_code} KR 드라이런: {ok}/{len(cards)}장 매칭")
    return ok


def crawl_promo_jp(set_code: str, cards: list[dict]) -> int:
    vers = PROMO_YUYU_VERS.get(set_code)
    if not vers:
        print(f"  JP: {set_code} — 유유테이 vers 없음, 스킵")
        return 0
    if not cards:
        return 0

    rate = get_exchange_rate()
    print(f"  JP: 유유테이 {vers}, 환율 JPY→KRW {rate}")

    rows: list[dict] = []
    ok = 0
    with httpx.Client(headers=YUYU_HEADERS, follow_redirects=True, timeout=30) as client:
        listings = fetch_set_listings(vers, client)
        if not listings:
            print(f"  JP: {set_code} — 유유테이 데이터 없음")
            return 0
        print(f"  JP: 유유테이 {len(listings)}건 수집")

        for card in cards:
            db_num = card.get("card_number") or ""
            hit = None
            for listing in listings.values():
                if card_numbers_match(db_num, listing.card_number):
                    hit = listing
                    break
            if hit:
                price_krw = round(hit.price_jpy * rate)
                _log(
                    f"  JP [{db_num or hit.card_number}] {card.get('name_jp') or hit.name_jp} "
                    f"=> ¥{hit.price_jpy:,} / ₩{price_krw:,}"
                )
                rows.append({
                    "card_id": card["id"],
                    "price_jpy": hit.price_jpy,
                    "price_krw": price_krw,
                    "source": "yuyutei",
                })
                ok += 1
            else:
                _log(f"  JP [{db_num}] {card.get('name_jp')} => 미등록")

    if APPLY and cards:
        all_ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_jp", all_ids, rows)
        print(f"  {set_code} JP 완료: {ok}/{len(cards)}장 (오늘 교체 {deleted}→{inserted})")
    return ok


def crawl_promo_set(set_code: str, region: str = "both") -> int:
    meta = PROMO_BY_CODE.get(set_code)
    if not meta:
        print(f"unknown promo set: {set_code}")
        return 1

    region = region.upper()
    if region not in ("KR", "JP", "BOTH"):
        region = "BOTH"

    _set_id, set_name, cards = load_promo_cards(set_code)
    print(f"\n=== {set_name}({set_code}) 프로모 시세 [{region}] ===")
    print(f"대상: {len(cards)}장")
    if not cards:
        return 0

    if region in ("KR", "BOTH"):
        crawl_promo_kr(set_code, set_name, cards, meta)
    if region in ("JP", "BOTH"):
        crawl_promo_jp(set_code, cards)
    return 0


def main() -> None:
    region = get_arg("--region", "both").lower()
    if region not in ("kr", "jp", "both"):
        region = "both"
    codes = promo_set_codes()
    failed = 0
    for code in codes:
        if crawl_promo_set(code, region=region) != 0:
            failed += 1
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
