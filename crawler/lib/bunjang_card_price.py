"""
번개장터 전용 카드 시세 수집 — KR / JP 공용.

정책:
  1) 거래완료(status=3, 180일 이내)와 판매중(status=0) 호가를 함께 평균
  2) 한 종류만 있으면 해당 가격으로 평균
  3) 단품 싱글만 (묶음·다량·다종 제외, 1장 판매만)
  4) 사진 3장 이상은 제외 (TRADE_CRAWL_CRITERIA.md §4)
"""
from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from lib.trade_sources import SOLD_MAX_AGE_DAYS
KST = timezone(timedelta(hours=9))
# 사진 1~2장은 단품으로 본다. 3장 이상은 다른 카드와 함께 올린 매물일 수 있다.
MAX_SINGLE_CARD_PHOTOS = 2
_image_count_cache: dict[str, dict | None] = {}
_image_count_lock = threading.Lock()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────────────
# API 조회
# ──────────────────────────────────────────────────

def fetch_bunjang_items(
    keyword: str,
    n: int = 100,
    *,
    page: int = 0,
    timeout: int = 5,
) -> list[dict]:
    """번개장터 검색 결과 (판매중 + 거래완료 모두 포함)."""
    encoded = urllib.parse.quote(keyword)
    url = (
        f"https://api.bunjang.co.kr/api/1/find_v2.json"
        f"?q={encoded}&n={n}&page={page}&order=date"
    )
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        res = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
        return json.loads(res).get("list", [])
    except Exception as e:
        print(f"[번개] {keyword[:30]!r} p{page} 오류: {e}")
        return []


def bunjang_product_detail(pid: str) -> dict | None:
    """상품 상세. imageCount·description. 검색 목록에는 둘 다 없다."""
    pid = str(pid or "").strip()
    if not pid.isdigit():
        return None
    with _image_count_lock:
        if pid in _image_count_cache:
            return _image_count_cache[pid]
    detail: dict | None
    try:
        url = f"https://api.bunjang.co.kr/api/pms/v1/products/{pid}/detail/web"
        req = urllib.request.Request(url, headers=_HEADERS)
        raw = urllib.request.urlopen(req, timeout=8).read()
        product = (json.loads(raw).get("data") or {}).get("product") or {}
        raw_count = product.get("imageCount")
        detail = {
            "imageCount": int(raw_count) if raw_count is not None else None,
            "description": str(product.get("description") or ""),
            "name": str(product.get("name") or ""),
        }
    except Exception:
        detail = None
    with _image_count_lock:
        _image_count_cache[pid] = detail
    return detail


def bunjang_product_image_count(pid: str) -> int | None:
    detail = bunjang_product_detail(pid)
    if not detail:
        return None
    count = detail.get("imageCount")
    return int(count) if count is not None else None


def listing_has_too_many_photos(item: dict) -> bool:
    """사진 3장 이상이면 True. 1~2장은 False. 장수를 모르면 제외하지 않는다."""
    raw = item.get("imageCount")
    if raw is None:
        raw = item.get("image_count")
    if raw is not None:
        try:
            return int(raw) >= MAX_SINGLE_CARD_PHOTOS + 1
        except (TypeError, ValueError):
            pass
    count = bunjang_product_image_count(str(item.get("pid") or ""))
    if count is None:
        return False
    return count >= MAX_SINGLE_CARD_PHOTOS + 1


def listing_blocked_by_product(item: dict) -> bool:
    """사진 3장 이상, 또는 상세 설명에만 있는 감정 점수면 제외."""
    from lib.price_search import text_has_slab_grade  # noqa: PLC0415

    if listing_has_too_many_photos(item):
        return True
    detail = bunjang_product_detail(str(item.get("pid") or ""))
    if not detail:
        return False
    blob = f"{detail.get('name') or ''}\n{detail.get('description') or ''}"
    return text_has_slab_grade(blob)


def _is_recent_sold(update_time: int) -> bool:
    """게시·거래 시각이 180일 이내인지. 시각이 없으면 유지한다."""
    if not update_time:
        return True
    now = datetime.now(timezone.utc).timestamp()
    return (now - update_time) <= SOLD_MAX_AGE_DAYS * 86400


def previous_kst_day_bounds() -> tuple[int, int]:
    """Return the previous KST calendar day as Unix timestamp bounds."""
    today = datetime.now(KST).date()
    end = datetime.combine(today, datetime.min.time(), tzinfo=KST)
    start = end - timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())


def is_previous_kst_day(update_time: int) -> bool:
    """Whether a Bunjang item's update/post time is from yesterday in KST."""
    if not update_time:
        return False
    start, end = previous_kst_day_bounds()
    return start <= int(update_time) < end


def filter_items_by_incremental_days(
    items: list[dict],
    incremental_days: list[date] | None,
) -> list[dict]:
    """incremental_days가 None이면 필터 없음, []이면 전부 제외."""
    if incremental_days is None:
        return items
    if not incremental_days:
        return []
    from lib.crawl_incremental import is_in_incremental_days  # noqa: PLC0415

    return [
        item for item in items
        if is_in_incremental_days(int(item.get("update_time", 0) or 0), incremental_days)
    ]


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
      - sold : status=3, 180일 이내
      - listing : status=0
    """
    sold_items, listing_items = split_by_status_kr_with_items(
        items, name_kr, rarity, card_number, set_code, set_name_kr
    )
    return [it["price"] for it in sold_items], [it["price"] for it in listing_items]


def split_by_status_kr_with_items(
    items: list[dict],
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
    set_name_kr: str,
    image_url: str = "",
) -> tuple[list[dict], list[dict]]:
    """
    KR 매물 → (sold_items, listing_items).
    각 item: {"price": int, "pid": str}
    """
    from lib.price_search import is_raw_kr_listing, parse_listing_quantity  # noqa: PLC0415

    sold: list[dict] = []
    listing: list[dict] = []

    referer = ""
    try:
        from kr_sets import KR_BY_CODE  # noqa: PLC0415
        meta = KR_BY_CODE.get(set_code)
        number = str(card_number).split("/", 1)[0].strip()
        if meta and meta.bs_code and number.isdigit():
            referer = f"https://pokemoncard.co.kr/cards/detail/{meta.bs_code}{int(number):03d}"
    except Exception:
        pass

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
            if parse_listing_quantity(title) > 1:
                continue
            if listing_blocked_by_product(item):
                continue

            status = str(item.get("status", ""))
            update_time = int(item.get("update_time", 0) or 0)
            pid = str(item.get("pid", ""))
            detail = {"price": price, "pid": pid, "update_time": update_time}

            if status == "3" and _is_recent_sold(update_time):
                sold.append(detail)
            elif status == "0" and _is_recent_sold(update_time):
                listing.append(detail)

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
    """JP 매물 → (sold_prices, listing_prices). 가격만 반환 (레거시 호환)."""
    sold_items, listing_items = split_by_status_jp_with_items(
        items, name_jp, name_kr, rarity, card_number
    )
    return [it["price"] for it in sold_items], [it["price"] for it in listing_items]


def split_by_status_jp_with_items(
    items: list[dict],
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    *,
    set_code: str = "",
    name_en: str = "",
    image_url: str = "",
) -> tuple[list[dict], list[dict]]:
    """
    JP 매물 → (sold_items, listing_items).
    각 item: {"price": int, "pid": str, "update_time": int}
    """
    from lib.jp_price_search import is_raw_jp_listing  # noqa: PLC0415
    from lib.price_search import parse_listing_quantity  # noqa: PLC0415

    sold: list[dict] = []
    listing: list[dict] = []

    for item in items:
            title = str(item.get("name", ""))
            try:
                price = int(item.get("price", 0) or 0)
            except (TypeError, ValueError):
                continue
            if price < 300 or price > 10_000_000:
                continue
            if not is_raw_jp_listing(
                title, name_jp, name_kr, rarity, card_number,
                name_en=name_en, set_code=set_code,
            ):
                continue
            if parse_listing_quantity(title) > 1:
                continue
            if listing_blocked_by_product(item):
                continue
            status = str(item.get("status", ""))
            update_time = int(item.get("update_time", 0) or 0)
            pid = str(item.get("pid", ""))
            detail = {"price": price, "pid": pid, "update_time": update_time}

            if status == "3" and _is_recent_sold(update_time):
                sold.append(detail)
            elif status == "0" and _is_recent_sold(update_time):
                listing.append(detail)

    return sold, listing


def sort_sold_items_by_time(items: list[dict]) -> list[dict]:
    """거래완료 항목을 update_time 내림차순 정렬."""
    return sorted(items, key=lambda x: int(x.get("update_time") or 0), reverse=True)


# ──────────────────────────────────────────────────
# 가격 결정
# ──────────────────────────────────────────────────

def collect_bunjang_items(
    queries: list[str],
    *,
    n: int = 100,
    early_stop_sold: int = 0,
) -> list[dict]:
    """검색어를 순서대로 실행 후 pid 기준 중복 제거.

    early_stop_sold: 이 수 이상의 거래완료(status=3) 매물이 모이면
    나머지 쿼리를 스킵한다 (0이면 항상 전부 실행, 거래내역 10건 수집용).
    """
    all_items: list[dict] = []
    seen_pids: set[str] = set()
    sold_count = 0

    max_pages = 3
    for q in queries:
        if not q:
            continue
        for page in range(max_pages):
            batch = fetch_bunjang_items(q, n=n, page=page)
            if not batch:
                break
            for it in batch:
                pid = str(it.get("pid", ""))
                if pid and pid in seen_pids:
                    continue
                if pid:
                    seen_pids.add(pid)
                all_items.append(it)
                if str(it.get("status", "")) == "3":
                    sold_count += 1
            if len(batch) < n:
                break

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

    - 거래완료와 판매중 호가가 있으면 두 가격을 함께 평균
    - 한 종류만 있으면 해당 가격으로 평균
    """
    sold = [p for p in sold if p > 0]
    listing = [p for p in listing if p > 0]
    values = sold + listing
    if values:
        avg = round(sum(values) / len(values))
        tier = "sold+listing" if sold and listing else ("sold" if sold else "listing")
        return avg, len(values), f"{tier}:{source_suffix}"
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
    incremental_days: list[date] | None = None,
    previous_day_only: bool = False,
) -> dict[int, tuple[list[int], list[int], list[dict], list[dict]]]:
    """카드 목록을 병렬로 번개장터 조회.

    incremental_days: None=전체, [date]=해당 KST 일자만 (catch-up·전날).
    previous_day_only: deprecated — incremental_days=[어제]와 동일.

    Returns: {card_id: (sold_prices, listing_prices, sold_items, listing_items)}
    """
    if previous_day_only and incremental_days is None:
        incremental_days = [
            datetime.now(KST).date() - timedelta(days=1)
        ]
    if not cards:
        return {}

    def _one(card: dict) -> tuple[int, tuple[list[int], list[int], list[dict], list[dict]]]:
        queries = build_queries_fn(
            set_name_kr,
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
        )
        all_items = collect_bunjang_items(queries)
        all_items = filter_items_by_incremental_days(all_items, incremental_days)
        sold_items, listing_items = split_by_status_kr_with_items(
            all_items,
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
            set_name_kr,
            card.get("image_url") or "",
        )
        sold = [it["price"] for it in sold_items]
        listing = [it["price"] for it in listing_items]
        return card["id"], (sold, listing, sold_items, listing_items)

    results: dict[int, tuple[list[int], list[int], list[dict], list[dict]]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(cards))) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            cid, triple = fut.result()
            if triple[0] or triple[1]:
                results[cid] = triple
    return results


# ──────────────────────────────────────────────────
# 병렬 프리페치 — JP
# ──────────────────────────────────────────────────

def prefetch_bunjang_jp(
    cards: list[dict],
    set_name_kr: str,
    set_code: str,
    *,
    build_queries_fn: Callable[..., list[str]] | None = None,
    workers: int = 8,
    incremental_days: list[date] | None = None,
    previous_day_only: bool = False,
) -> dict[int, tuple[list[int], list[int], list[dict], list[dict]]]:
    """JP 카드 목록 → {card_id: (sold_prices, listing_prices, sold_items, listing_items)}."""
    if previous_day_only and incremental_days is None:
        incremental_days = [
            datetime.now(KST).date() - timedelta(days=1)
        ]
    from lib.jp_price_search import build_jp_search_queries  # noqa: PLC0415
    from lib.price_search import is_legacy_set  # noqa: PLC0415

    if not cards:
        return {}

    _slim = is_legacy_set(set_code)

    def _one(card: dict) -> tuple[int, tuple[list[int], list[int], list[dict], list[dict]]]:
        if build_queries_fn is not None:
            queries = build_queries_fn(
                set_name_kr,
                card.get("name_kr") or "",
                card.get("rarity") or "",
                card.get("card_number") or "",
                set_code,
            )
        else:
            queries = build_jp_search_queries(
                set_name_kr,
                card.get("name_jp") or "",
                card.get("name_kr") or "",
                card.get("rarity") or "",
                card.get("card_number") or "",
                set_code,
                slim=_slim,
                name_en=card.get("name_en") or "",
            )
        all_items = collect_bunjang_items(queries)
        all_items = filter_items_by_incremental_days(all_items, incremental_days)
        sold_items, listing_items = split_by_status_jp_with_items(
            all_items,
            card.get("name_jp") or "",
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code=set_code,
            name_en=card.get("name_en") or "",
            image_url=card.get("image_url") or "",
        )
        sold = [it["price"] for it in sold_items]
        listing = [it["price"] for it in listing_items]
        return card["id"], (sold, listing, sold_items, listing_items)

    results: dict[int, tuple[list[int], list[int], list[dict], list[dict]]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(cards))) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            cid, quad = fut.result()
            if quad[0] or quad[1]:
                results[cid] = quad
    return results
