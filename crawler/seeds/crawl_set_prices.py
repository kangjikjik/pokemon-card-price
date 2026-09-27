"""
KR 확장팩 카드 시세 — 번개장터 전용.

정책: crawler/TRADE_CRAWL_CRITERIA.md
  - 번개장터 거래완료(180일) + 판매중 호가를 함께 평균
  - 단품 싱글만 (묶음·다량·다종 제외, qty=1)

  python crawl_set_prices.py --set MG6
  python crawl_set_prices.py --set MG6 --apply
  python crawl_set_prices.py --set MG6 --apply --missing-only
  python crawl_set_prices.py --set MG6 --apply --rarity AR
"""
from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.bunjang_card_price import (  # noqa: E402
    collect_bunjang_items,
    prefetch_bunjang_kr,
    resolve_card_price,
    sort_sold_items_by_time,
    split_by_status_kr,
)
from lib.price_history import (  # noqa: E402
    save_daily_snapshots,
    save_incremental_snapshots,
)
from lib.price_search import (  # noqa: E402
    build_search_queries,
    is_legacy_set,
)
from lib.trade_reconcile import (  # noqa: E402
    apply_outlier_filter,
    build_historical_by_card,
    outlier_detail_ids_to_drop,
)
from lib.trade_sources import BUNJANG_NONE, BUNJANG_NONE_NO_DETAIL  # noqa: E402
from kr_sets import KR_BY_CODE  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.trainer_item_cards import is_trainer_or_item_card  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv
MISSING_ONLY = "--missing-only" in sys.argv
TRAINER_ITEM_ONLY = "--trainer-item-only" in sys.argv
from lib.crawl_incremental import (  # noqa: E402
    exit_if_caught_up,
    get_incremental_days,
    is_incremental_mode,
    print_incremental_banner,
    read_last_crawl_kst,
)

INCREMENTAL_DAYS = get_incremental_days(sys.argv, sb)
DAILY_INCREMENTAL = is_incremental_mode(INCREMENTAL_DAYS)
WORKERS = 16
MAX_SOLD_ROWS = 100


def _append_bunjang_rows(
    out: list[dict],
    items: list[dict],
    tier: str,
    card_id: int,
) -> None:
    """tier: sold | listing — sold:bunjang:PID:TS 또는 listing:bunjang:PID:TS"""
    for it in sort_sold_items_by_time(items)[:MAX_SOLD_ROWS]:
        pid = it.get("pid", "")
        if not pid:
            continue
        ts = it.get("update_time", 0)
        src = f"{tier}:bunjang:{pid}:{ts}" if ts else f"{tier}:bunjang:{pid}"
        out.append({"card_id": card_id, "price_krw": it["price"], "source": src})


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


ONLY_RARITY = get_arg("--rarity", "").upper()
ONLY_CARD_NUMBER = get_arg("--card-number", "")


def _build_queries(
    set_name_kr: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
) -> list[str]:
    slim = is_legacy_set(set_code)  # SM/XY 등 구형 팩은 쿼리 3개로 줄임
    return build_search_queries(set_name_kr, name_kr, rarity, card_number, set_code, slim=slim)


def _log(msg: str) -> None:
    if not QUIET:
        print(msg)


def resolve_set_code(raw: str) -> str:
    """MG5a·SV8a 등 소문자 접미사 보존 (DB set_code와 일치)."""
    key = raw.strip().upper()
    for code in KR_BY_CODE:
        if code.upper() == key:
            return code
    return raw.strip()


def crawl_card(
    card: dict,
    set_name_kr: str,
    set_code: str,
    *,
    prefetched: tuple[list[int], list[int], list[dict], list[dict]] | None = None,
    historical: tuple[list[int], list[int]] | None = None,
) -> tuple[int, int, str, list[dict], list[dict], bool]:
    """(price, count, source, sold_items, listing_items, no_detail)"""
    name_kr = card.get("name_kr") or ""
    rarity = card.get("rarity") or ""
    card_number = card.get("card_number") or ""

    if prefetched is not None:
        sold, listing, sold_items, listing_items = prefetched
    else:
        from lib.bunjang_card_price import split_by_status_kr_with_items  # noqa: PLC0415
        queries = _build_queries(set_name_kr, name_kr, rarity, card_number, set_code)
        all_items = collect_bunjang_items(queries)
        sold_items_raw, listing_items_raw = split_by_status_kr_with_items(
            all_items, name_kr, rarity, card_number, set_code, set_name_kr
        )
        sold = [it["price"] for it in sold_items_raw]
        listing = [it["price"] for it in listing_items_raw]
        sold_items = sold_items_raw
        listing_items = listing_items_raw

    historical_sold, historical_listing = historical or ([], [])
    # 기존 상세도 같이 판정한다. 탈락한 과거 가격은 평균에 다시 넣지 않는다.
    sold_filtered, listing_filtered, sold_items, listing_items = apply_outlier_filter(
        historical_sold,
        historical_listing,
        sold_items,
        listing_items,
        rarity,
    )

    price, count, source = resolve_card_price(sold_filtered, listing_filtered)
    no_detail = False
    if price > 0 and not sold_items and not listing_items:
        no_detail = True
        price, count, source = 0, 0, "none"
    return price, count, source, sold_items, listing_items, no_detail


def main() -> None:
    if not QUIET and INCREMENTAL_DAYS is not None:
        print_incremental_banner(INCREMENTAL_DAYS, last_crawl=read_last_crawl_kst(sb))
    exit_if_caught_up(INCREMENTAL_DAYS, last_crawl=read_last_crawl_kst(sb))

    set_code = resolve_set_code(get_arg("--set", ""))
    if not set_code:
        print("사용법: python crawl_set_prices.py --set MG6 [--apply]")
        sys.exit(1)

    row = sb.table("card_sets").select("id,set_code,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print(f"=== {set_code} — DB 세트 없음 (스킵) ===")
        return
    set_id = row[0]["id"]
    set_name = row[0]["name_kr"]

    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity")
        .eq("set_id", set_id)
        .order("card_number")
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    if TRAINER_ITEM_ONLY:
        cards = [
            c for c in cards
            if is_trainer_or_item_card(set_code, c.get("card_number") or "")
        ]
    if ONLY_RARITY:
        cards = [c for c in cards if (c.get("rarity") or "").upper() == ONLY_RARITY]
    if ONLY_CARD_NUMBER:
        cards = [c for c in cards if (c.get("card_number") or "") == ONLY_CARD_NUMBER]
    if MISSING_ONLY:
        priced_ids = {
            r["card_id"]
            for r in (
                sb.table("prices_kr")
                .select("card_id")
                .in_("card_id", [c["id"] for c in cards])
                .gt("price_krw", 0)
                .execute()
                .data
                or []
            )
        }
        cards = [c for c in cards if c["id"] not in priced_ids]

    suffix = ""
    if ONLY_RARITY:
        suffix += f" ({ONLY_RARITY}만)"
    if MISSING_ONLY:
        suffix += " (미등록만)"
    print(f"=== {set_name}({set_code}) KR 시세 [번개장터 전용] ===")
    print(f"대상: {len(cards)}장{suffix}")
    if not APPLY:
        print("드라이런 — 반영: --apply 추가")
        cards = cards[:5]

    # 병렬 번개장터 조회
    print(f"번개장터 병렬 조회 중 (workers={WORKERS})...")
    historical_by_card: dict[int, tuple[list[int], list[int]]] = {}
    if DAILY_INCREMENTAL:
        history_rows = (
            sb.table("prices_kr")
            .select("id,card_id,price_krw,source")
            .in_("card_id", [c["id"] for c in cards])
            .gt("price_krw", 0)
            .execute()
            .data
            or []
        )
        historical_by_card = build_historical_by_card(history_rows)
        if APPLY:
            drop_ids = outlier_detail_ids_to_drop(
                history_rows,
                {int(c["id"]): c.get("rarity") or "" for c in cards},
            )
            for i in range(0, len(drop_ids), 200):
                sb.table("prices_kr").delete().in_("id", drop_ids[i : i + 200]).execute()
            if drop_ids:
                print(f"이상치 상세 삭제: {len(drop_ids)}건")
                historical_by_card = build_historical_by_card(
                    [row for row in history_rows if row.get("id") not in set(drop_ids)]
                )

    prefetch = prefetch_bunjang_kr(
        cards,
        set_name,
        set_code,
        build_queries_fn=_build_queries,
        workers=WORKERS,
        incremental_days=INCREMENTAL_DAYS,
    )
    print(f"조회 완료: {len(prefetch)}/{len(cards)}장 매칭")

    ok = 0
    priced_rows: list[dict] = []

    for card in cards:
        quad = prefetch.get(card["id"])
        if DAILY_INCREMENTAL and quad is None:
            continue
        _log(f"\n[{card['card_number']}] {card['name_kr']} ({card['rarity']})")
        price, count, source, sold_items, listing_items, no_detail = crawl_card(
            card, set_name, set_code, prefetched=quad,
            historical=historical_by_card.get(card["id"]),
        )

        if count > 0:
            tier = "거래완료+호가" if source.startswith("sold+listing") else (
                "거래완료" if source.startswith("sold") else "호가"
            )
            _log(f"  => {price:,}원 ({count}건, {tier})")
        else:
            _log("  => 미등록")

        if APPLY:
            card_rows: list[dict] = []
            if price > 0:
                # 목록·상세 대표가 (개별 거래 row와 분리)
                card_rows.append({"card_id": card["id"], "price_krw": price, "source": source})
                if sold_items:
                    _append_bunjang_rows(card_rows, sold_items, "sold", card["id"])
                if listing_items:
                    _append_bunjang_rows(card_rows, listing_items, "listing", card["id"])
                ok += 1
            else:
                card_rows.append({
                    "card_id": card["id"],
                    "price_krw": 0,
                    "source": BUNJANG_NONE_NO_DETAIL if no_detail else BUNJANG_NONE,
                })
            priced_rows.extend(card_rows)

    if APPLY:
        all_ids = (
            [c["id"] for c in cards if c["id"] in prefetch]
            if DAILY_INCREMENTAL
            else [c["id"] for c in cards]
        )
        save_fn = save_incremental_snapshots if DAILY_INCREMENTAL else save_daily_snapshots
        deleted, inserted = save_fn(sb, "prices_kr", all_ids, priced_rows)
        unpriced = len(cards) - ok
        print(
            f"\n완료: {ok}장 저장"
            f" (교체 {deleted}→{inserted}"
            + (f", 미등록 {unpriced}장" if unpriced else ")")
        )
    else:
        print("\n(드라이런 샘플 5장만 조회)")


if __name__ == "__main__":
    main()
