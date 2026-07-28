"""Collectory 일본판(region=jp) 카드 ID 조회·거래내역."""
from __future__ import annotations

import httpx

from lib.collectory_prices import card_num_key
from lib.collectory_public import (
    fetch_collectory_public_quotes_jp,
    preload_public_quotes_jp,
    public_quotes_to_trades,
)
from lib.jp_price_search import JP_RARITY_EQUIV
from lib.price_resolve import PriceQuote

COLLECTORY_API = "https://collectory.cc/api"


def _rarity_match(card_rarity: str, target: str) -> bool:
    cr = (card_rarity or "").upper()
    tr = (target or "").upper()
    if cr == tr:
        return True
    equiv = JP_RARITY_EQUIV.get(tr, set())
    if cr in equiv:
        return True
    if tr in ("MUR",) and cr in ("UR", "MUR"):
        return True
    if tr in ("P", "PROMO") and cr in ("P", "PROMO", "프로모"):
        return True
    return False


def search_collectory_jp_card_id(
    name_jp: str,
    name_kr: str,
    card_number: str,
    rarity: str,
    client: httpx.Client,
) -> str:
    """collectory 검색 API — region=jp 카드 ID."""
    queries = []
    if name_jp:
        queries.extend([
            f"{name_jp} {card_number}".strip(),
            f"{card_number} {name_jp}".strip(),
            name_jp,
        ])
    if name_kr:
        queries.append(f"{name_kr} {card_number}".strip())
    if card_number:
        queries.append(card_number)

    seen: set[str] = set()
    for q in queries:
        q = q.strip()
        if not q or q in seen:
            continue
        seen.add(q)
        res = client.get(f"{COLLECTORY_API}/cards/search", params={"q": q}, timeout=20)
        if res.status_code != 200:
            continue
        for card in res.json().get("results", {}).get("cards") or []:
            if (card.get("region") or "").lower() != "jp":
                continue
            if not _rarity_match(card.get("rarity") or "", rarity):
                continue
            num = card.get("cardNumber") or card.get("card_number") or ""
            if card_number and num and card_num_key(num) != card_num_key(card_number):
                continue
            cid = (card.get("card_id") or card.get("id") or "").strip()
            if cid:
                return cid
    return ""


def build_jp_card_id_map(
    cards: list[dict],
    client: httpx.Client,
    *,
    workers: int = 8,
) -> dict[int, str]:
    """DB card id → collectory jp card_id."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    out: dict[int, str] = {}

    def _one(card: dict) -> tuple[int, str]:
        cid = search_collectory_jp_card_id(
            card.get("name_jp") or "",
            card.get("name_kr") or "",
            card.get("card_number") or "",
            card.get("rarity") or "",
            client,
        )
        return card["id"], cid

    w = min(workers, max(len(cards), 1))
    with ThreadPoolExecutor(max_workers=w) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            db_id, col_id = fut.result()
            if col_id:
                out[db_id] = col_id
    return out


def resolve_jp_collectory_trades(
    collectory_card_id: str,
    client: httpx.Client | None,
    *,
    preloaded: list[PriceQuote] | None = None,
) -> tuple[list[int], list[int], list[str], list[str]]:
    """체결(메ルカ리·SNKRDUNK·카페) + 호가(번개·크림)."""
    if preloaded is not None:
        quotes = preloaded
    else:
        quotes = fetch_collectory_public_quotes_jp(collectory_card_id, client)
    pub = public_quotes_to_trades(quotes)
    return pub.sold, pub.listings, pub.sold_sources, pub.listing_sources
