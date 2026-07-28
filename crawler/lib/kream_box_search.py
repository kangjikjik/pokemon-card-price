"""크림(KREAM) 박스 시세 — 거래/호가 조회 (가능할 때만).

공식 API는 인증·토큰이 필요해 무인증 요청은 대부분 실패한다.
KREAM_WEB_TOKEN 환경변수가 있으면 api.kream.co.kr 검색을 시도한다.
실패 시 빈 목록 — 번개장터 시세만 사용.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from lib.box_price_search import resolve_box_price

KREAM_SEARCH_API = "https://api.kream.co.kr/api/se/products/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Origin": "https://kream.co.kr",
    "Referer": "https://kream.co.kr/",
}


def _kream_headers() -> dict[str, str]:
    h = dict(DEFAULT_HEADERS)
    token = os.getenv("KREAM_WEB_TOKEN", "").strip()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def build_kr_box_kream_queries(set_name_kr: str, set_code: str) -> list[str]:
    name = set_name_kr.strip()
    code = set_code.strip().upper()
    queries = [
        f"포켓몬 {name} 박스",
        f"포켓몬카드 {name} 박스 미개봉",
        f"포켓몬 TCG {name} 박스",
        f"포켓몬카드 {code} 박스",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def build_jp_box_kream_queries(set_name_kr: str, set_code: str, jp_name: str = "") -> list[str]:
    name = set_name_kr.strip()
    code = set_code.strip().upper()
    queries = [
        f"포켓몬 {name} 일본판 박스",
        f"포켓몬카드 {name} JP 박스",
        f"포켓몬 {name} 일본 박스 미개봉",
        f"포켓몬카드 {code} 일본판 박스",
    ]
    if jp_name:
        queries.append(f"포켓몬 {jp_name} ボックス")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _extract_prices_from_items(items: list[Any]) -> list[int]:
    prices: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in (
            "last_sale_price",
            "lastSalePrice",
            "lowest_ask",
            "lowestAsk",
            "market_price",
            "marketPrice",
            "price",
        ):
            val = item.get(key)
            if isinstance(val, (int, float)) and val > 0:
                prices.append(int(val))
                break
    return prices


def _fetch_kream_search(keyword: str, client: httpx.Client) -> list[int]:
    """KREAM 검색 API — 토큰 없으면 보통 실패."""
    try:
        res = client.get(
            KREAM_SEARCH_API,
            params={"keyword": keyword, "per_page": 20, "cursor": 1},
            timeout=15,
        )
        if res.status_code != 200:
            return []
        data = res.json()
        items = data.get("items") or data.get("products") or data.get("results") or []
        if isinstance(items, dict):
            items = items.get("items") or []
        return _extract_prices_from_items(items if isinstance(items, list) else [])
    except Exception:
        return []


def fetch_kream_box_prices(
    queries: list[str],
    *,
    filter_fn,
    set_name_kr: str,
    set_code: str,
    msrp: int,
    client: httpx.Client | None = None,
) -> tuple[list[int], bool]:
    """
    filter_fn: filter_bunjang_box_listings 또는 filter_bunjang_jp_box_listings 와 동일 시그니처.
    크림 직접 API가 실패하면 번개 검색 API로 크림 매물명을 재사용할 수 없으므로 API 가격만 반환.
    Returns (prices, api_reachable).
    """
    own = client is None
    if own:
        client = httpx.Client(headers=_kream_headers(), follow_redirects=True)

    api_ok = False
    all_prices: list[int] = []
    try:
        for q in queries[:3]:
            raw = _fetch_kream_search(q, client)
            if raw:
                api_ok = True
                # MSRP 밴드만 적용 (제목 필터 없음 — API 결과는 이미 키워드 매칭)
                lo = max(3000, int(msrp * 0.25))
                hi = max(lo + 1000, int(msrp * 4.0))
                for p in raw:
                    if lo <= p <= hi:
                        all_prices.append(p)
    finally:
        if own:
            client.close()

    return all_prices, api_ok


def merge_box_prices(*price_lists: list[int]) -> tuple[int, int]:
    """여러 소스 호가 합쳐 중앙값."""
    merged: list[int] = []
    for lst in price_lists:
        merged.extend(p for p in lst if p > 0)
    return resolve_box_price(merged)
