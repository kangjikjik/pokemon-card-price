"""collectory.cc 카드 상세 페이지 공개 거래내역 (카페/Break 체결, 번개·쇼핑 호가)."""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx

from lib.price_resolve import PriceQuote, classify_collectory_row, is_graded_grade

COLLECTORY_CARD_URL = "https://collectory.cc/cards/{card_id}"
TR_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
PRICE_RE = re.compile(r"₩\s*([\d,]+)")

# 페이지 렌더 테이블 출처 → 정규화
SOURCE_ALIASES: dict[str, str] = {
    "네이버카페": "naver_cafe",
    "번개장터": "bunjang",
    "네이버쇼핑": "naver_shopping",
    "break": "break",
    "Break": "break",
    "BREAK": "break",
    "킨들샵": "kream",
    "TCGBox": "tcgbox",
    "KREAM": "kream",
}

_PAGE_CACHE: dict[str, tuple[float, list[PriceQuote]]] = {}
_CACHE_TTL_SEC = 300


@dataclass(frozen=True)
class PublicTradeIndex:
    sold: list[int]
    listings: list[int]
    sold_sources: list[str]
    listing_sources: list[str]


def _normalize_source(raw: str, row_html: str) -> str:
    if "cardmvk/" in row_html:
        return "naver_cafe"
    if "break.market" in row_html.lower():
        return "break"
    key = (raw or "").strip()
    return SOURCE_ALIASES.get(key, key.lower() or "unknown")


def _row_text(row_html: str) -> list[str]:
    text = re.sub(r"<[^>]+>", "|", row_html)
    text = re.sub(r"\|+", "|", text)
    return [p.strip() for p in text.split("|") if p.strip()]


def _parse_transaction_row(row_html: str) -> PriceQuote | None:
    if not any(
        token in row_html
        for token in ("cardmvk/", "번개장터", "네이버쇼핑", "네이버카페", "break.market", "Break", "킨들샵", "TCGBox")
    ):
        return None

    price_m = PRICE_RE.search(row_html)
    if not price_m:
        return None
    price = int(price_m.group(1).replace(",", ""))
    if price < 100 or price > 50_000_000:
        return None

    parts = _row_text(row_html)
    source_raw = parts[1] if len(parts) > 1 else ""
    grade = parts[2] if len(parts) > 2 else "Single"
    title = parts[-1] if parts else ""

    if is_graded_grade(grade):
        return None
    t_upper = title.upper()
    if any(k in t_upper for k in ("PSA", "BRG", "BGS", "CGC", "슬랩", "일판", "JP ", "영문판", "일어판")):
        return None

    source = _normalize_source(source_raw, row_html)
    tier = classify_collectory_row(source, grade, title)
    if tier is None:
        return None
    return PriceQuote(price_krw=price, tier=tier, source=source, title=title)


def _parse_page_quotes(html: str) -> list[PriceQuote]:
    quotes: list[PriceQuote] = []
    for row_html in TR_ROW_RE.findall(html):
        q = _parse_transaction_row(row_html)
        if q:
            quotes.append(q)
    return quotes


def fetch_collectory_public_quotes(
    card_id: str,
    client: httpx.Client | None = None,
    *,
    use_cache: bool = True,
) -> list[PriceQuote]:
    """카드 상세 페이지 Transactions 테이블 파싱 (인증 불필요)."""
    cid = (card_id or "").strip()
    if not cid:
        return []

    now = time.time()
    if use_cache and cid in _PAGE_CACHE:
        ts, cached = _PAGE_CACHE[cid]
        if now - ts < _CACHE_TTL_SEC:
            return list(cached)

    own = client is None
    if own:
        client = httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"})

    quotes: list[PriceQuote] = []
    try:
        res = client.get(COLLECTORY_CARD_URL.format(card_id=cid))
        if res.status_code != 200:
            return []
        quotes = _parse_page_quotes(res.text)
        if use_cache:
            _PAGE_CACHE[cid] = (now, list(quotes))
    finally:
        if own:
            client.close()
    return quotes


def preload_public_quotes(
    card_ids: list[str],
    client: httpx.Client,
    *,
    workers: int = 20,
) -> dict[str, list[PriceQuote]]:
    """세트 단위 collectory 카드 페이지 병렬 프리로드."""
    ids = [c.strip() for c in card_ids if c and c.strip()]
    if not ids:
        return {}

    now = time.time()
    out: dict[str, list[PriceQuote]] = {}
    todo: list[str] = []
    for cid in ids:
        if cid in _PAGE_CACHE and now - _PAGE_CACHE[cid][0] < _CACHE_TTL_SEC:
            out[cid] = list(_PAGE_CACHE[cid][1])
        else:
            todo.append(cid)

    if not todo:
        return out

    def _fetch_one(card_id: str) -> tuple[str, list[PriceQuote]]:
        res = client.get(COLLECTORY_CARD_URL.format(card_id=card_id))
        if res.status_code != 200:
            return card_id, []
        quotes = _parse_page_quotes(res.text)
        _PAGE_CACHE[card_id] = (time.time(), list(quotes))
        return card_id, quotes

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, cid): cid for cid in todo}
        for fut in as_completed(futures):
            cid, quotes = fut.result()
            out[cid] = quotes

    return out


def public_quotes_to_trades(quotes: list[PriceQuote]) -> PublicTradeIndex:
    sold: list[int] = []
    listings: list[int] = []
    sold_src: list[str] = []
    listing_src: list[str] = []
    for q in quotes:
        if q.tier == "sold":
            sold.append(q.price_krw)
            sold_src.append(q.source)
        elif q.tier == "listing":
            listings.append(q.price_krw)
            listing_src.append(q.source)
    return PublicTradeIndex(sold, listings, sold_src, listing_src)
