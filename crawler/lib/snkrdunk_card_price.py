"""
SNKRDUNK JP 체결가 — Collectory 공개 거래내역에서 SNKRDUNK sold 행만 추출.

SNKRDUNK는 공식 거래내역 API가 없어, Collectory가 집계한 SNKRDUNK 체결 행을 사용한다.
(메ルカリ·카페 등 다른 Collectory 출처는 사용하지 않음)

정책:
  - tier=sold, source=snkrdunk 만
  - RAW/Single/Cond.A~C (PSA·BRG·D급 등 제외 — collectory_public 파서 + price_resolve)
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import httpx

from lib.collectory_jp import build_jp_card_id_map
from lib.collectory_public import preload_public_quotes_jp
from lib.price_resolve import PriceQuote

SNKRDUNK_PID_RE = re.compile(r"snkrdunk\.com/apparels/(\d+)", re.I)


def _snkrdunk_product_id(url: str) -> str:
    m = SNKRDUNK_PID_RE.search(url or "")
    return m.group(1) if m else ""


def snkrdunk_sold_from_quotes(quotes: list[PriceQuote]) -> list[int]:
    """PriceQuote 목록 → SNKRDUNK 체결가(KRW)만."""
    return [
        q.price_krw
        for q in quotes
        if q.tier == "sold" and q.source == "snkrdunk" and q.price_krw > 0
    ]


def snkrdunk_sold_items_from_quotes(quotes: list[PriceQuote]) -> list[dict]:
    """PriceQuote 목록 → SNKRDUNK 개별 체결 (가격·URL·날짜)."""
    items: list[dict] = []
    for q in quotes:
        if q.tier != "sold" or q.source != "snkrdunk" or q.price_krw <= 0:
            continue
        pid = _snkrdunk_product_id(q.url)
        items.append({
            "price": q.price_krw,
            "url": q.url,
            "trade_date": q.trade_date,
            "product_id": pid,
        })
    return filter_snkrdunk_price_outliers(items)


def filter_snkrdunk_price_outliers(items: list[dict]) -> list[dict]:
    """같은 카드 SNKRDUNK 체결 중 중앙값 대비 비정상 고가 제거 (슬랩 유출 방어)."""
    if len(items) < 3:
        return items
    prices = sorted(it["price"] for it in items)
    med = prices[len(prices) // 2]
    cap = max(int(med * 2.5), med + 30_000)
    return [it for it in items if it["price"] <= cap]


def build_snkrdunk_source(item: dict) -> str:
    """DB source 필드 — sold:snkrdunk:PID:YYYY-MM-DD"""
    pid = item.get("product_id") or _snkrdunk_product_id(item.get("url") or "")
    date = item.get("trade_date") or ""
    if pid and date:
        return f"sold:snkrdunk:{pid}:{date}"
    if pid:
        return f"sold:snkrdunk:{pid}"
    return "sold:snkrdunk"


def prefetch_snkrdunk_sold_jp(
    cards: list[dict],
    client: httpx.Client,
    *,
    workers: int = 4,
) -> dict[int, list[dict]]:
    """{card_id: [{price, url, trade_date, product_id}, ...]}. Collectory ID 매칭 실패 시 제외."""
    if not cards:
        return {}

    col_map = build_jp_card_id_map(cards, client, workers=min(workers, len(cards)))
    if not col_map:
        return {}

    quotes_by_col = preload_public_quotes_jp(
        list(col_map.values()),
        client,
        workers=min(workers, 4),
    )

    out: dict[int, list[dict]] = {}
    for db_id, col_id in col_map.items():
        quotes = quotes_by_col.get(col_id, [])
        sold = snkrdunk_sold_items_from_quotes(quotes)
        if sold:
            # trade_date 내림차순 (없으면 뒤로)
            sold.sort(key=lambda x: x.get("trade_date") or "", reverse=True)
            out[db_id] = sold
    return out


def merge_jp_card_price(
    bunjang_sold: list[int],
    bunjang_listing: list[int],
    snkrdunk_sold: list[int],
) -> tuple[int, int, str]:
    """
    JP 대표가 — 번개장터 + SNKRDUNK 병합.

    1) bunjang sold + snkrdunk sold → 전체 평균, source=sold:bunjang+snkrdunk (해당 출처만)
    2) sold 없으면 bunjang listing 최저 → listing:bunjang
    3) 둘 다 없으면 (0, 0, none)
    """
    sold = [p for p in bunjang_sold + snkrdunk_sold if p > 0]
    if sold:
        avg = round(sum(sold) / len(sold))
        parts: list[str] = []
        if any(p > 0 for p in bunjang_sold):
            parts.append("bunjang")
        if any(p > 0 for p in snkrdunk_sold):
            parts.append("snkrdunk")
        return avg, len(sold), "sold:" + "+".join(parts)

    listing = [p for p in bunjang_listing if p > 0]
    if listing:
        return min(listing), len(listing), "listing:bunjang"
    return 0, 0, "none"
