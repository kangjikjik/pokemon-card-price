"""일본판 확장팩 시세 — Collectory JP·번개 일판 (KR와 동일 정책). 유유테i는 --fallback 전용."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from lib.collectory_jp import resolve_jp_collectory_trades
from lib.collectory_prices import merge_collectory_primary
from lib.jp_price_search import (
    build_jp_search_queries,
    filter_bunjang_jp_listings,
)
from lib.price_resolve import PriceQuote, LISTING_HIGH_TIER_MEDIAN
from lib.price_search import (
    calculate_conservative_price,
    calculate_median_price,
    calculate_trimmed_mean,
)
from lib.yuyutei_prices import YuyuListing, fetch_card_listing

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

BUNJANG_WORKERS = 8


def fetch_bunjang(keyword: str) -> list[dict]:
    encoded = urllib.parse.quote(keyword)
    url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded}&n=50"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        res = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        return json.loads(res).get("list", [])
    except Exception:
        return []


def _has_bunjang_listing(sources: list[str]) -> bool:
    return any(
        s in ("bunjang", "번개장터") or "bunjang" in (s or "").lower()
        for s in sources
    )


def _fetch_bunjang_jp_prices(
    set_name_kr: str,
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
    *,
    fast: bool,
) -> list[int]:
    queries = build_jp_search_queries(
        set_name_kr, name_jp, name_kr, rarity, card_number, set_code
    )
    limit = 1 if fast else 3
    all_prices: list[int] = []
    for q in queries[:limit]:
        items = fetch_bunjang(q)
        all_prices.extend(
            filter_bunjang_jp_listings(items, name_jp, name_kr, rarity, card_number)
        )
        if all_prices:
            break
    return list(dict.fromkeys(all_prices))


def _drop_suspicious_sold(
    sold: list[int],
    listings: list[int],
    sold_src: list[str],
    rarity: str,
) -> tuple[list[int], list[str]]:
    """체결가가 호가 대비 지나치게 낮으면(하자/D급 등) 체결 제외."""
    if not sold or not listings:
        return sold, sold_src
    sold_ref = calculate_median_price(sold)
    r = (rarity or "").upper()
    if r in LISTING_HIGH_TIER_MEDIAN:
        list_ref = calculate_median_price(listings)
    else:
        list_ref = min(listings)
    if list_ref > 0 and sold_ref < list_ref * 0.55:
        return [], []
    return sold, sold_src


def prefetch_bunjang_jp(
    cards: list[dict],
    set_name_kr: str,
    set_code: str,
    *,
    fast: bool,
) -> dict[int, list[int]]:
    if not cards:
        return {}

    def _one(card: dict) -> tuple[int, list[int]]:
        return card["id"], _fetch_bunjang_jp_prices(
            set_name_kr,
            card.get("name_jp") or "",
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
            fast=fast,
        )

    out: dict[int, list[int]] = {}
    workers = min(BUNJANG_WORKERS, len(cards))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            cid, prices = fut.result()
            if prices:
                out[cid] = prices
    return out


def cards_needing_bunjang_jp(
    cards: list[dict],
    id_map: dict[int, str],
    quote_cache: dict[str, list[PriceQuote]],
) -> list[dict]:
    need: list[dict] = []
    for card in cards:
        cid = id_map.get(card["id"], "")
        if not cid:
            need.append(card)
            continue
        sold, _listings, _ss, listing_src = resolve_jp_collectory_trades(
            cid, None, preloaded=quote_cache.get(cid)
        )
        if not sold and not _has_bunjang_listing(listing_src):
            need.append(card)
    return need


def resolve_jp_card_price(
    card: dict,
    *,
    collectory_id: str,
    quote_cache: dict[str, list[PriceQuote]],
    bunjang_cache: dict[int, list[int]] | None,
    rate: float,
    set_name_kr: str,
    set_code: str,
    fast: bool,
) -> tuple[int, int, int, str, int]:
    """Collectory JP + 번개 일판만. Returns median_krw, low, count, source, price_jpy(0)."""
    sold: list[int] = []
    listings: list[int] = []
    sold_src: list[str] = []
    listing_src: list[str] = []

    if collectory_id:
        sold, listings, sold_src, listing_src = resolve_jp_collectory_trades(
            collectory_id, None, preloaded=quote_cache.get(collectory_id)
        )
        sold, sold_src = _drop_suspicious_sold(
            sold, listings, sold_src, card.get("rarity") or ""
        )

    extra_bj: list[int] = []
    if bunjang_cache is not None and card["id"] in bunjang_cache:
        extra_bj = list(bunjang_cache[card["id"]])
    elif bunjang_cache is None and not _has_bunjang_listing(listing_src):
        extra_bj = _fetch_bunjang_jp_prices(
            set_name_kr,
            card.get("name_jp") or "",
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
            fast=fast,
        )
    if extra_bj:
        listings = list(listings) + extra_bj
        listing_src = list(listing_src) + ["bunjang"] * len(extra_bj)

    median, low, n, source = merge_collectory_primary(
        0,
        [],
        calculate_median_price=calculate_median_price,
        calculate_trimmed_mean=calculate_trimmed_mean,
        calculate_conservative_price=calculate_conservative_price,
        rarity=card.get("rarity") or "",
        sold_prices=sold,
        listing_prices=listings,
        sold_sources=sold_src,
        listing_sources=listing_src,
    )
    return median, low, n, source, 0


def apply_jp_kr_guard(
    card: dict,
    median: int,
    low: int,
    n: int,
    source: str,
    price_jpy: int,
    *,
    kr_price: int,
    rate: float,
    collectory_id: str,
    quote_cache: dict[str, list[PriceQuote]],
    bunjang_cache: dict[int, list[int]] | None,
    set_name_kr: str,
    set_code: str,
    fast: bool,
    vers: str,
    yuyu_client: httpx.Client | None,
) -> tuple[int, int, int, str, int]:
    """
    JP < KR 이면 시장 데이터(유유테i·Collectory 호가·번개 일판·체결)만 재조회.
    KR 가격으로 인위 보정하지 않음.
    """
    if kr_price <= 0 or median <= 0 or median >= kr_price:
        return median, low, n, source, price_jpy

    candidates: list[tuple[int, int, int, str, int]] = [
        (median, low, n, source, price_jpy),
    ]

    def _add(m: int, l: int, cnt: int, src: str, jpy: int) -> None:
        if m > 0:
            candidates.append((m, l, cnt, src, jpy))

    if vers and yuyu_client is not None:
        ym, yl, yn, ys, yj = try_yuyutei_fallback(
            card, vers=vers, rate=rate, client=yuyu_client
        )
        if yn > 0:
            _add(ym, yl, yn, ys, yj)

    if collectory_id:
        sold, listings, sold_src, listing_src = resolve_jp_collectory_trades(
            collectory_id, None, preloaded=quote_cache.get(collectory_id)
        )
        extra_bj = list((bunjang_cache or {}).get(card["id"], []))
        if not extra_bj:
            extra_bj = _fetch_bunjang_jp_prices(
                set_name_kr,
                card.get("name_jp") or "",
                card.get("name_kr") or "",
                card.get("rarity") or "",
                card.get("card_number") or "",
                set_code,
                fast=False,
            )
        if extra_bj:
            listings = list(listings) + extra_bj
            listing_src = list(listing_src) + ["bunjang"] * len(extra_bj)
        sold, sold_src = _drop_suspicious_sold(
            sold, listings, sold_src, card.get("rarity") or ""
        )
        if listings:
            lm, ll, ln, ls = merge_collectory_primary(
                0,
                [],
                calculate_median_price=calculate_median_price,
                calculate_trimmed_mean=calculate_trimmed_mean,
                calculate_conservative_price=calculate_conservative_price,
                rarity=card.get("rarity") or "",
                sold_prices=[],
                listing_prices=listings,
                listing_sources=listing_src,
            )
            if ln > 0:
                _add(lm, ll, ln, ls, round(lm / rate) if rate else 0)
        if sold:
            sm, sl, sn, ss = merge_collectory_primary(
                0,
                [],
                calculate_median_price=calculate_median_price,
                calculate_trimmed_mean=calculate_trimmed_mean,
                calculate_conservative_price=calculate_conservative_price,
                rarity=card.get("rarity") or "",
                sold_prices=sold,
                sold_sources=sold_src,
            )
            if sn > 0:
                _add(sm, sl, sn, ss, round(sm / rate) if rate else 0)

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0]


def try_yuyutei_fallback(
    card: dict,
    *,
    vers: str,
    rate: float,
    client: httpx.Client,
) -> tuple[int, int, int, str, int]:
    """유유테i 호가 1장 조회."""
    hit = fetch_card_listing(
        vers,
        card.get("card_number") or "",
        card.get("name_jp") or "",
        card.get("rarity") or "",
        client,
    )
    if not hit or hit.price_jpy <= 0:
        return 0, 0, 0, "none", 0
    krw = round(hit.price_jpy * rate)
    return krw, krw, 1, "listing:yuyutei", hit.price_jpy
