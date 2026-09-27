"""
JP 확장팩 카드 시세 — 번개장터 전용.

정책: crawler/TRADE_CRAWL_CRITERIA.md
  - 번개장터 거래완료(180일) + 판매중 호가를 함께 평균
  - 일본판 표기·KR 대비 하한·단품 싱글(qty=1)

  python crawl_set_prices_jp.py --set MG6
  python crawl_set_prices_jp.py --set MG6 --apply
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.bunjang_card_price import (  # noqa: E402
    prefetch_bunjang_jp,
    resolve_card_price,
    sort_sold_items_by_time,
)
from lib.price_history import (  # noqa: E402
    save_daily_snapshots,
    save_incremental_snapshots,
)
from lib.jp_price_search import (  # noqa: E402
    filter_jp_items_by_kr_floor,
    filter_jp_prices_by_kr_floor,
)
from lib.kr_reference_prices import load_kr_reference_prices  # noqa: E402
from lib.trade_reconcile import (  # noqa: E402
    apply_outlier_filter,
    build_historical_by_card,
    outlier_detail_ids_to_drop,
)
from lib.trade_sources import BUNJANG_NONE, BUNJANG_NONE_NO_DETAIL  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.trainer_item_cards import is_trainer_or_item_card  # noqa: E402
from kr_sets import KR_BY_CODE, KR_SETS  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv
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
WORKERS = 16          # 번개장터 병렬
MAX_SOLD_ROWS = 100


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


ONLY_RARITY = get_arg("--rarity", "").upper()
ONLY_CARD_NUMBER = get_arg("--card-number", "")


def _append_bunjang_jp_rows(
    out: list[dict],
    items: list[dict],
    tier: str,
    card_id: int,
    rate: float,
) -> None:
    for it in sort_sold_items_by_time(items)[:MAX_SOLD_ROWS]:
        pid = it.get("pid", "")
        if not pid:
            continue
        ts = it.get("update_time", 0)
        src = f"{tier}:bunjang:{pid}:{ts}" if ts else f"{tier}:bunjang:{pid}"
        out.append({
            "card_id": card_id,
            "price_jpy": round(it["price"] / rate) if rate else 0,
            "price_krw": it["price"],
            "source": src,
        })


def get_exchange_rate() -> float:
    key = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
    if key:
        try:
            r = httpx.get(
                f"https://v6.exchangerate-api.com/v6/{key}/pair/JPY/KRW",
                timeout=10,
            )
            return float(r.json()["conversion_rate"])
        except Exception:
            pass
    return 9.5


def _log(msg: str) -> None:
    if not QUIET:
        print(msg)


def resolve_set_code(raw: str) -> str:
    key = raw.strip().upper()
    for code in KR_BY_CODE:
        if code.upper() == key:
            return code
    return raw.strip().upper()


def crawl_one(set_code: str, rate: float) -> tuple[int, int]:
    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print(f"=== {set_code} — DB 세트 없음 ===")
        return 0, 0
    set_name = row[0]["name_kr"]
    set_id = row[0]["id"]

    cards = (
        sb.table("cards")
        .select("id,card_number,name_jp,name_kr,name_en,rarity")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    if ONLY_RARITY:
        cards = [c for c in cards if (c.get("rarity") or "").upper() == ONLY_RARITY]
    if ONLY_CARD_NUMBER:
        cards = [c for c in cards if (c.get("card_number") or "") == ONLY_CARD_NUMBER]
    if TRAINER_ITEM_ONLY:
        cards = [
            c for c in cards
            if is_trainer_or_item_card(set_code, c.get("card_number") or "")
        ]
    if not cards:
        print(f"=== {set_name}({set_code}) — 대상 카드 없음 ===")
        return 0, 0

    suffix = ""
    if ONLY_CARD_NUMBER:
        suffix = f" ({ONLY_CARD_NUMBER}만)"
    elif ONLY_RARITY:
        suffix = f" ({ONLY_RARITY}만)"
    print(f"=== {set_name}({set_code}) JP 시세 [번개장터 전용]{suffix} ===")
    print(f"대상: {len(cards)}장")

    kr_refs = load_kr_reference_prices(sb, [c["id"] for c in cards])

    bunjang_prefetch = prefetch_bunjang_jp(
        cards,
        set_name,
        set_code,
        workers=WORKERS,
        incremental_days=INCREMENTAL_DAYS,
    )
    print(f"번개 조회 완료: {len(bunjang_prefetch)}/{len(cards)}장 매칭")

    historical_by_card: dict[int, tuple[list[int], list[int]]] = {}
    if DAILY_INCREMENTAL:
        history_rows = (
            sb.table("prices_jp")
            .select("id,card_id,price_krw,source")
            .in_("card_id", [c["id"] for c in cards])
            .gt("price_krw", 0)
            .execute()
            .data
            or []
        )
        if APPLY:
            drop_ids = outlier_detail_ids_to_drop(
                history_rows,
                {int(c["id"]): c.get("rarity") or "" for c in cards},
                kr_floor_by_card=kr_refs,
            )
            for i in range(0, len(drop_ids), 200):
                sb.table("prices_jp").delete().in_("id", drop_ids[i : i + 200]).execute()
            if drop_ids:
                print(f"이상치 상세 삭제: {len(drop_ids)}건")
                history_rows = [row for row in history_rows if row.get("id") not in set(drop_ids)]
        historical_by_card = build_historical_by_card(history_rows)

    rows: list[dict] = []
    ok = 0

    for card in cards:
        cid = card["id"]
        if DAILY_INCREMENTAL and cid not in bunjang_prefetch:
            continue
        if cid in bunjang_prefetch:
            b_sold, b_listing, b_sold_items, b_listing_items = bunjang_prefetch[cid]
        else:
            b_sold, b_listing, b_sold_items, b_listing_items = [], [], [], []

        rarity = card.get("rarity") or ""
        historical_sold, historical_listing = historical_by_card.get(cid, ([], []))
        kr_floor = kr_refs.get(cid, 0)
        if kr_floor > 0:
            b_sold_items = filter_jp_items_by_kr_floor(b_sold_items, kr_floor)
            b_listing_items = filter_jp_items_by_kr_floor(b_listing_items, kr_floor)
            historical_sold = filter_jp_prices_by_kr_floor(historical_sold, kr_floor)
            historical_listing = filter_jp_prices_by_kr_floor(historical_listing, kr_floor)
            b_sold = [it["price"] for it in b_sold_items]
            b_listing = [it["price"] for it in b_listing_items]
        b_sold, b_listing, b_sold_items, b_listing_items = apply_outlier_filter(
            historical_sold,
            historical_listing,
            b_sold_items,
            b_listing_items,
            rarity,
        )

        price_krw, count, source = resolve_card_price(b_sold, b_listing)
        no_detail = False
        if price_krw > 0 and not b_sold_items and not b_listing_items:
            no_detail = True
            price_krw, count, source = 0, 0, "none"

        if count > 0:
            price_jpy = round(price_krw / rate) if rate else 0
            if source.startswith("sold"):
                tier = "거래완료"
            else:
                tier = "호가최저"
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')}"
                f" ({rarity}) => ₩{price_krw:,} / ¥{price_jpy:,} ({count}건, {tier}, {source})"
            )

            card_rows: list[dict] = []
            card_rows.append({
                "card_id": card["id"],
                "price_krw": price_krw,
                "price_jpy": price_jpy,
                "source": source,
            })
            if b_sold_items:
                _append_bunjang_jp_rows(card_rows, b_sold_items, "sold", card["id"], rate)
            if b_listing_items:
                _append_bunjang_jp_rows(card_rows, b_listing_items, "listing", card["id"], rate)
            if not card_rows:
                card_rows.append({
                    "card_id": card["id"],
                    "price_krw": 0,
                    "price_jpy": 0,
                    "source": BUNJANG_NONE_NO_DETAIL if no_detail else BUNJANG_NONE,
                })
            if card_rows:
                rows.extend(card_rows)
                ok += 1
        else:
            if APPLY:
                rows.append({
                    "card_id": card["id"],
                    "price_krw": 0,
                    "price_jpy": 0,
                    "source": BUNJANG_NONE_NO_DETAIL if no_detail else BUNJANG_NONE,
                })
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')}"
                f" ({rarity}) => 미등록"
            )

    if APPLY:
        ids = (
            [c["id"] for c in cards if c["id"] in bunjang_prefetch]
            if DAILY_INCREMENTAL
            else [c["id"] for c in cards]
        )
        save_fn = save_incremental_snapshots if DAILY_INCREMENTAL else save_daily_snapshots
        deleted, inserted = save_fn(sb, "prices_jp", ids, rows)
        print(f"완료: {ok}/{len(cards)}장 저장 (교체 {deleted}→{inserted})")
    else:
        print(f"드라이런: {ok}/{len(cards)}장 매칭")

    return ok, len(cards)


def main() -> None:
    if not QUIET and INCREMENTAL_DAYS is not None:
        print_incremental_banner(INCREMENTAL_DAYS, last_crawl=read_last_crawl_kst(sb))
    exit_if_caught_up(INCREMENTAL_DAYS, last_crawl=read_last_crawl_kst(sb))

    targets: list[str] = []
    set_code = resolve_set_code(get_arg("--set", ""))
    if set_code:
        targets = [set_code]
    elif "--all" in sys.argv:
        targets = [s.code for s in KR_SETS]
    else:
        print("사용법:")
        print("  python crawl_set_prices_jp.py --set MG6 [--apply]")
        print("  python crawl_set_prices_jp.py --all --apply")
        sys.exit(1)

    rate = get_exchange_rate()
    print(f"환율 JPY→KRW: {rate}")

    total_ok = total_cards = 0
    for i, code in enumerate(targets):
        if i > 0:
            print()
        ok, n = crawl_one(code, rate)
        total_ok += ok
        total_cards += n

    if len(targets) > 1:
        print(f"\n합계: {total_ok}/{total_cards}장")


if __name__ == "__main__":
    main()
