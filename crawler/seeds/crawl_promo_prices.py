"""
프로모(P) 카드 시세 — KR/JP 모두 번개장터 전용.

  python crawl_promo_prices.py --apply
  python crawl_promo_prices.py --set CEL25PK --apply --region KR
  python crawl_promo_prices.py --apply --region JP

일일 배치: KR/JP 확장팩 배치 끝에 --region KR|JP 로 자동 호출.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.bunjang_card_price import (  # noqa: E402
    prefetch_bunjang_jp,
    prefetch_bunjang_kr,
    resolve_card_price,
    sort_sold_items_by_time,
)
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.price_search import (  # noqa: E402
    build_promo_search_queries,
    filter_prices_by_rarity_band,
)
from lib.rarity_rank import is_promo_rarity  # noqa: E402
from crawl_set_prices import APPLY, MISSING_ONLY, QUIET, WORKERS, _log, crawl_card, get_arg  # noqa: E402
from crawl_set_prices_jp import get_exchange_rate  # noqa: E402
from promo_catalog import PROMO_BY_CODE, PROMO_SET_CODES  # noqa: E402
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


def _build_promo_queries(
    set_name_kr: str,
    name_kr: str,
    _rarity: str,
    card_number: str,
    set_code: str,
) -> list[str]:
    return build_promo_search_queries(
        name_kr,
        card_number,
        promo_source=set_name_kr,
        set_code=set_code,
    )


def crawl_promo_kr(set_code: str, set_name: str, cards: list[dict]) -> int:
    if not cards:
        return 0

    print(f"  KR: 번개장터 전용 (workers={WORKERS})")
    prefetch = prefetch_bunjang_kr(
        cards,
        set_name,
        set_code,
        build_queries_fn=_build_promo_queries,
        workers=WORKERS,
    )
    print(f"  번개 조회: {len(prefetch)}/{len(cards)}장 매칭")

    ok = 0
    priced_rows: list[dict] = []
    for card in cards:
        _log(f"\n[{card['card_number']}] {card['name_kr']} (P)")
        pair = prefetch.get(card["id"])
        price, count, source, sold_items, _listing_items = crawl_card(
            card,
            set_name,
            set_code,
            prefetched=pair,
        )
        if count > 0:
            tier = "거래완료" if source.startswith("sold") else "호가최저"
            _log(f"  => {price:,}원 ({count}건, {tier})")
        else:
            _log("  => 미등록")
        if APPLY and price > 0:
            # 일반 확장팩과 동일하게 대표 시세 요약 행을 먼저 저장한다.
            # 개별 거래 행은 상세 링크·실제 거래일 표시용으로 함께 저장한다.
            priced_rows.append({
                "card_id": card["id"],
                "price_krw": price,
                "source": source,
            })
            if source.startswith("sold") and sold_items:
                for it in sort_sold_items_by_time(sold_items)[:10]:
                    pid = it.get("pid", "")
                    ts = it.get("update_time", 0)
                    if pid and ts:
                        src = f"sold:bunjang:{pid}:{ts}"
                    elif pid:
                        src = f"sold:bunjang:{pid}"
                    else:
                        continue
                    priced_rows.append({"card_id": card["id"], "price_krw": it["price"], "source": src})
            else:
                priced_rows.append({"card_id": card["id"], "price_krw": price, "source": source})
            ok += 1

    if APPLY and cards:
        all_ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_kr", all_ids, priced_rows)
        print(f"\n{set_code} KR 완료: {ok}/{len(cards)}장 (오늘 교체 {deleted}→{inserted})")
    else:
        print(f"\n{set_code} KR 드라이런: {ok}/{len(cards)}장 매칭")
    return ok


def crawl_promo_jp(set_code: str, set_name: str, cards: list[dict]) -> int:
    if not cards:
        return 0

    rate = get_exchange_rate()
    print(f"  JP: 번개장터 전용, 환율 JPY→KRW {rate}")

    bunjang_prefetch = prefetch_bunjang_jp(cards, set_name, set_code, workers=WORKERS)
    print(f"  번개 조회: {len(bunjang_prefetch)}/{len(cards)}장")

    rows: list[dict] = []
    ok = 0
    for card in cards:
        cid = card["id"]
        if cid in bunjang_prefetch:
            b_sold, b_listing, b_sold_items, _b_listing_items = bunjang_prefetch[cid]
        else:
            b_sold, b_listing, b_sold_items = [], [], []
        rarity = card.get("rarity") or "P"
        b_sold = filter_prices_by_rarity_band(b_sold, rarity)
        b_listing = filter_prices_by_rarity_band(b_listing, rarity)
        b_sold_items = [it for it in b_sold_items if filter_prices_by_rarity_band([it["price"]], rarity)]
        price_krw, count, source = resolve_card_price(b_sold, b_listing)
        if count > 0:
            price_jpy = round(price_krw / rate) if rate else 0
            _log(
                f"  JP [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')}"
                f" => ₩{price_krw:,} / ¥{price_jpy:,} ({count}건, {source})"
            )
            # 일반 JP 확장팩과 동일하게 대표 시세 요약 행을 저장한다.
            rows.append({
                "card_id": card["id"],
                "price_krw": price_krw,
                "price_jpy": price_jpy,
                "source": source,
            })
            if source.startswith("sold:"):
                for it in sort_sold_items_by_time(b_sold_items)[:10]:
                    pid = it.get("pid", "")
                    ts = it.get("update_time", 0)
                    if not pid:
                        continue
                    src = f"sold:bunjang:{pid}:{ts}" if ts else f"sold:bunjang:{pid}"
                    rows.append({
                        "card_id": card["id"],
                        "price_jpy": round(it["price"] / rate) if rate else 0,
                        "price_krw": it["price"],
                        "source": src,
                    })
            ok += 1
        else:
            _log(f"  JP [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')} => 미등록")

    if APPLY and cards:
        all_ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_jp", all_ids, rows)
        print(f"  {set_code} JP 완료: {ok}/{len(cards)}장 (오늘 교체 {deleted}→{inserted})")
    return ok


def crawl_promo_set(set_code: str, region: str = "both") -> int:
    if set_code not in PROMO_BY_CODE:
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
        crawl_promo_kr(set_code, set_name, cards)
    if region in ("JP", "BOTH"):
        crawl_promo_jp(set_code, set_name, cards)
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
