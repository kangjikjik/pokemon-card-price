"""
번개장터 전용 카드 시세 수집 — KR / JP 공용.

정책:
  1) 거래완료(status=3, 90일 이내) → 평균가
  2) 없으면 판매중(status=0) 최저가
  3) 단품 싱글만 (묶음·다량·다종 제외, 1장 판매만)
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable

SOLD_MAX_AGE_DAYS = 90

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────────────
# API 조회
# ──────────────────────────────────────────────────

def fetch_bunjang_items(keyword: str, n: int = 100, *, timeout: int = 5) -> list[dict]:
    """번개장터 검색 결과 (판매중 + 거래완료 모두 포함)."""
    encoded = urllib.parse.quote(keyword)
    url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded}&n={n}"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        res = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
        return json.loads(res).get("list", [])
    except Exception as e:
        print(f"[번개] {keyword[:30]!r} 오류: {e}")
        return []


def _is_recent_sold(update_time: int) -> bool:
    """거래완료 시각이 90일 이내인지."""
    if not update_time:
        return True
    now = datetime.now(timezone.utc).timestamp()
    return (now - update_time) <= SOLD_MAX_AGE_DAYS * 86400


# ──────────────────────────────────────────────────
# KR 매물 분류
# ──────────────────────────────────────────────────

def split_by_status_kr(
    items: list[dict],
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
    set_name_kr: str,
) -> tuple[list[int], list[int]]:
    """
    KR 매물 → (sold_prices, listing_prices).

    통과 기준:
      - is_raw_kr_listing (미등급·한글판·단품)
      - qty == 1 (2장 이상 묶음 제외)
      - sold : status=3, 90일 이내
      - listing : status=0
    """
    from lib.price_search import is_raw_kr_listing, parse_listing_quantity  # noqa: PLC0415

    sold: list[int] = []
    listing: list[int] = []

    for item in items:
        title = str(item.get("name", ""))
        try:
            price = int(item.get("price", 0) or 0)
        except (TypeError, ValueError):
            continue
        if price < 300 or price > 5_000_000:
            continue
        if not is_raw_kr_listing(title, name_kr, rarity, card_number, set_code, set_name_kr):
            continue
        # 다장 매물 제외 — qty > 1 은 스킵 (단가 환산하지 않음)
        if parse_listing_quantity(title) > 1:
            continue

        status = str(item.get("status", ""))
        update_time = int(item.get("update_time", 0) or 0)

        if status == "3" and _is_recent_sold(update_time):
            sold.append(price)
        elif status == "0":
            listing.append(price)

    return sold, listing


# ──────────────────────────────────────────────────
# JP 매물 분류
# ──────────────────────────────────────────────────

def split_by_status_jp(
    items: list[dict],
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str,
) -> tuple[list[int], list[int]]:
    """
    JP 매물 → (sold_prices, listing_prices).

    통과 기준:
      - is_raw_jp_listing (일본판 미등급 단품)
      - qty == 1
      - sold : status=3, 90일 이내
      - listing : status=0
    """
    from lib.jp_price_search import is_raw_jp_listing  # noqa: PLC0415
    from lib.price_search import parse_listing_quantity  # noqa: PLC0415

    sold: list[int] = []
    listing: list[int] = []

    for item in items:
        title = str(item.get("name", ""))
        try:
            price = int(item.get("price", 0) or 0)
        except (TypeError, ValueError):
            continue
        if price < 300 or price > 10_000_000:
            continue
        if not is_raw_jp_listing(title, name_jp, name_kr, rarity, card_number):
            continue
        if parse_listing_quantity(title) > 1:
            continue

        status = str(item.get("status", ""))
        update_time = int(item.get("update_time", 0) or 0)

        if status == "3" and _is_recent_sold(update_time):
            sold.append(price)
        elif status == "0":
            listing.append(price)

    return sold, listing


# ──────────────────────────────────────────────────
# 가격 결정
# ──────────────────────────────────────────────────

def collect_bunjang_items(
    queries: list[str],
    *,
    n: int = 100,
    early_stop_sold: int = 3,
) -> list[dict]:
    """검색어를 순서대로 실행 후 pid 기준 중복 제거.

    early_stop_sold: 이 수 이상의 거래완료(status=3) 매물이 모이면
    나머지 쿼리를 스킵한다 (0이면 항상 전부 실행).
    """
    all_items: list[dict] = []
    seen_pids: set[str] = set()
    sold_count = 0

    for q in queries:
        if not q:
            continue
        for it in fetch_bunjang_items(q, n=n):
            pid = str(it.get("pid", ""))
            if pid and pid in seen_pids:
                continue
            if pid:
                seen_pids.add(pid)
            all_items.append(it)
            if str(it.get("status", "")) == "3":
                sold_count += 1

        # 충분한 거래완료가 모이면 나머지 쿼리 스킵
        if early_stop_sold > 0 and sold_count >= early_stop_sold:
            break

    return all_items


def resolve_card_price(
    sold: list[int],
    listing: list[int],
    source_suffix: str = "bunjang",
) -> tuple[int, int, str]:
    """
    (price, count, source).

    - sold 있으면: 평균(average)
    - sold 없으면: 판매중 최저가(min)
    - 둘 다 없으면: (0, 0, "none")
    """
    if sold:
        avg = round(sum(sold) / len(sold))
        return avg, len(sold), f"sold:{source_suffix}"
    if listing:
        return min(listing), len(listing), f"listing:{source_suffix}"
    return 0, 0, "none"


# ──────────────────────────────────────────────────
# 병렬 프리페치 — KR
# ──────────────────────────────────────────────────

def prefetch_bunjang_kr(
    cards: list[dict],
    set_name_kr: str,
    set_code: str,
    *,
    build_queries_fn: Callable[[str, str, str, str, str], list[str]],
    workers: int = 8,
) -> dict[int, tuple[list[int], list[int]]]:
    """카드 목록을 병렬로 번개장터 조회 → {card_id: (sold_prices, listing_prices)}."""
    if not cards:
        return {}

    def _one(card: dict) -> tuple[int, tuple[list[int], list[int]]]:
        queries = build_queries_fn(
            set_name_kr,
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
        )
        all_items = collect_bunjang_items(queries)
        sold, listing = split_by_status_kr(
            all_items,
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
            set_name_kr,
        )
        return card["id"], (sold, listing)

    results: dict[int, tuple[list[int], list[int]]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(cards))) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            cid, pair = fut.result()
            if pair[0] or pair[1]:
                results[cid] = pair
    return results


# ──────────────────────────────────────────────────
# 병렬 프리페치 — JP
# ──────────────────────────────────────────────────

def prefetch_bunjang_jp(
    cards: list[dict],
    set_name_kr: str,
    set_code: str,
    *,
    workers: int = 8,
) -> dict[int, tuple[list[int], list[int]]]:
    """JP 카드 목록을 병렬로 번개장터 조회 → {card_id: (sold_prices, listing_prices)}."""
    from lib.jp_price_search import build_jp_search_queries  # noqa: PLC0415
    from lib.price_search import is_legacy_set  # noqa: PLC0415

    if not cards:
        return {}

    _slim = is_legacy_set(set_code)

    def _one(card: dict) -> tuple[int, tuple[list[int], list[int]]]:
        queries = build_jp_search_queries(
            set_name_kr,
            card.get("name_jp") or card.get("name_kr") or "",
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
            slim=_slim,
        )
        all_items = collect_bunjang_items(queries)
        sold, listing = split_by_status_jp(
            all_items,
            card.get("name_jp") or "",
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
        )
        return card["id"], (sold, listing)

    results: dict[int, tuple[list[int], list[int]]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(cards))) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            cid, pair = fut.result()
            if pair[0] or pair[1]:
                results[cid] = pair
    return results
