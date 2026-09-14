"""
KR 확장팩 카드 시세 — 번개장터 전용.

정책 (crawler/PRICING.md):
  1) 번개장터 거래완료(status=3, 90일 이내) → 평균가
  2) 없으면 번개장터 판매중(status=0) 최저가
  3) 단품 싱글만 (묶음·다량·다종 제외, qty=1 한 장만)

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
    split_by_status_kr,
)
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.price_search import (  # noqa: E402
    build_search_queries,
    filter_prices_by_rarity_band,
    is_legacy_set,
)
from kr_sets import KR_BY_CODE  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv
MISSING_ONLY = "--missing-only" in sys.argv
WORKERS = 16


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


ONLY_RARITY = get_arg("--rarity", "").upper()


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
    prefetched: tuple[list[int], list[int]] | None = None,
) -> tuple[int, int, str]:
    """(price, count, source) — 번개장터 거래완료 평균 → 호가최저 순."""
    name_kr = card.get("name_kr") or ""
    rarity = card.get("rarity") or ""
    card_number = card.get("card_number") or ""

    if prefetched is not None:
        sold, listing = prefetched
    else:
        queries = _build_queries(set_name_kr, name_kr, rarity, card_number, set_code)
        all_items = collect_bunjang_items(queries)
        sold, listing = split_by_status_kr(
            all_items, name_kr, rarity, card_number, set_code, set_name_kr
        )

    # 등급별 이상치 필터
    sold = filter_prices_by_rarity_band(sold, rarity)
    listing = filter_prices_by_rarity_band(listing, rarity)

    return resolve_card_price(sold, listing)


def main() -> None:
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
    if ONLY_RARITY:
        cards = [c for c in cards if (c.get("rarity") or "").upper() == ONLY_RARITY]
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
    prefetch = prefetch_bunjang_kr(
        cards,
        set_name,
        set_code,
        build_queries_fn=_build_queries,
        workers=WORKERS,
    )
    print(f"조회 완료: {len(prefetch)}/{len(cards)}장 매칭")

    ok = 0
    priced_rows: list[dict] = []

    for card in cards:
        _log(f"\n[{card['card_number']}] {card['name_kr']} ({card['rarity']})")
        pair = prefetch.get(card["id"])
        price, count, source = crawl_card(card, set_name, set_code, prefetched=pair)

        if count > 0:
            tier = "거래완료" if source.startswith("sold") else "호가최저"
            _log(f"  => {price:,}원 ({count}건, {tier})")
        else:
            _log("  => 미등록")

        if APPLY and price > 0:
            priced_rows.append({
                "card_id": card["id"],
                "price_krw": price,
                "source": source,
            })
            ok += 1

    if APPLY:
        all_ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_kr", all_ids, priced_rows)
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
