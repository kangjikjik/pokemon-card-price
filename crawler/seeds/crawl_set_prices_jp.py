"""
JP 확장팩 카드 시세 — 번개장터 전용.

정책 (crawler/PRICING.md):
  1) 번개장터 거래완료(status=3, 90일 이내) → 평균가
  2) 체결 없으면 번개장터 판매중(status=0) 최저가
  3) 단품 싱글만 (일본판 표기, qty=1)

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
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.price_search import MIN_SOLD_FOR_AGGREGATE, filter_prices_pipeline  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.trainer_item_cards import is_trainer_or_item_card  # noqa: E402
from kr_sets import KR_BY_CODE, KR_SETS  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv
TRAINER_ITEM_ONLY = "--trainer-item-only" in sys.argv
WORKERS = 16          # 번개장터 병렬
MAX_SOLD_ROWS = 100


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


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


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
    if TRAINER_ITEM_ONLY:
        cards = [
            c for c in cards
            if is_trainer_or_item_card(set_code, c.get("card_number") or "")
        ]
    if not cards:
        print(f"=== {set_name}({set_code}) — 대상 카드 없음 ===")
        return 0, 0

    print(f"=== {set_name}({set_code}) JP 시세 [번개장터 전용] ===")
    print(f"대상: {len(cards)}장")

    bunjang_prefetch = prefetch_bunjang_jp(cards, set_name, set_code, workers=WORKERS)
    print(f"번개 조회 완료: {len(bunjang_prefetch)}/{len(cards)}장 매칭")

    rows: list[dict] = []
    ok = 0

    for card in cards:
        cid = card["id"]
        if cid in bunjang_prefetch:
            b_sold, b_listing, b_sold_items, b_listing_items = bunjang_prefetch[cid]
        else:
            b_sold, b_listing, b_sold_items, b_listing_items = [], [], [], []

        rarity = card.get("rarity") or ""
        b_sold = filter_prices_pipeline(b_sold, rarity)
        b_listing = filter_prices_pipeline(b_listing, rarity)
        sold_ok = set(b_sold)
        list_ok = set(b_listing)
        b_sold_items = [it for it in b_sold_items if it["price"] in sold_ok]
        b_listing_items = [it for it in b_listing_items if it["price"] in list_ok]

        price_krw, count, source = resolve_card_price(b_sold, b_listing)

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
            if b_listing_items and len(b_sold_items) < MIN_SOLD_FOR_AGGREGATE:
                _append_bunjang_jp_rows(card_rows, b_listing_items, "listing", card["id"], rate)
            if card_rows:
                rows.extend(card_rows)
                ok += 1
        else:
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')}"
                f" ({rarity}) => 미등록"
            )

    if APPLY:
        ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_jp", ids, rows)
        print(f"완료: {ok}/{len(cards)}장 저장 (교체 {deleted}→{inserted})")
    else:
        print(f"드라이런: {ok}/{len(cards)}장 매칭")

    return ok, len(cards)


def main() -> None:
    targets: list[str] = []
    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        targets = [resolve_set_code(s) for s in sys.argv[idx + 1:] if not s.startswith("-")]
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
