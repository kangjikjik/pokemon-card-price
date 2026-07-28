"""collectory.cc 한글판 시세 조회 (미등급·KR 검증)."""
from __future__ import annotations

import os
import re

import httpx

from lib.collectory_public import fetch_collectory_public_quotes, public_quotes_to_trades
from lib.price_resolve import PriceQuote, classify_collectory_row
from lib.price_search import unit_price_from_listing

COLLECTORY_API = "https://collectory.cc/api"

# SR 이상: collectory set API price_krw 는 최저가일 수 있음 → 마켓 평균 우선
HIGH_TIER_RARITIES = frozenset({
    "SR", "SAR", "MUR", "MA", "UR", "ACE", "HR", "SSR", "CSR", "CHR", "PR", "TR", "RRR", "BWR", "FUR",
})


def card_num_key(num: str) -> tuple[int, str]:
    num = (num or "").strip()
    if "/" not in num:
        return (0, num)
    left, right = num.split("/", 1)
    try:
        return (int(left), right)
    except ValueError:
        return (0, num)


def norm_name(name: str) -> str:
    return re.sub(r"\s+", "", (name or "").strip()).lower()


# DB 카드명 ↔ collectory 명칭 차이 (어비스아이 등)
COLLECTORY_NAME_ALIASES: dict[str, list[str]] = {
    "아이언디펜더": ["아이언디펜드업"],
    "에너지전환": ["에너지갈아달기"],
    "클래시해머": ["크래시해머"],
    "다크펜던트": ["다크펜던트"],
    "강화폭탄": ["강화폭탄"],
    "브레이브뱅글": ["브레이브뱅글"],
    "이슬의활기": ["이슬의기력"],
    "그라지오의결전": ["글라디오의결전"],
    "녹슨조의심부름꾼": ["녹청파의조무래기"],
    "메ga몰드류ex": ["메ga몰드류ex", "메몰드류ex"],
}


def name_variants(name_kr: str) -> set[str]:
    base = norm_name(name_kr)
    variants = {base}
    for alias in COLLECTORY_NAME_ALIASES.get(base, []):
        variants.add(norm_name(alias))
    return variants


def is_kr_raw_collectory_card(card: dict) -> bool:
    """collectory region=kr 항목만 사용 (JP·CN·US region 제외)."""
    return (card.get("region") or "").lower() == "kr"


class CollectoryPriceIndex:
    def __init__(self) -> None:
        self.by_number: dict[tuple[int, str, str], int] = {}
        self.by_name: dict[tuple[str, str], int] = {}
        self.card_ids: dict[tuple[int, str, str], str] = {}
        self.card_ids_by_name: dict[tuple[str, str], str] = {}

    def add(
        self,
        card_number: str,
        name_ko: str,
        rarity: str,
        price: int,
        card_id: str = "",
    ) -> None:
        r = (rarity or "").upper()
        num_key = (*card_num_key(card_number), r)
        name_key = (norm_name(name_ko), r)
        cid = (card_id or "").strip()
        if num_key not in self.by_number or price < self.by_number[num_key]:
            self.by_number[num_key] = price
        if name_key not in self.by_name or price < self.by_name[name_key]:
            self.by_name[name_key] = price
        if cid:
            self.card_ids[num_key] = cid
            self.card_ids_by_name[name_key] = cid

    def lookup_card_id(self, card_number: str, name_kr: str, rarity: str) -> str:
        r = (rarity or "").upper()
        for variant in name_variants(name_kr):
            if (variant, r) in self.card_ids_by_name:
                return self.card_ids_by_name[(variant, r)]
        num_key = (*card_num_key(card_number), r)
        return self.card_ids.get(num_key, "")

    def lookup(self, card_number: str, name_kr: str, rarity: str) -> int:
        r = (rarity or "").upper()

        # 이름 우선 (DB·collectory 카드번호 불일치 대응)
        for variant in name_variants(name_kr):
            if (variant, r) in self.by_name:
                return self.by_name[(variant, r)]

        target = norm_name(name_kr)
        variants = name_variants(name_kr)
        if len(target) >= 3:
            best = 0
            best_score = 0
            for (n, ra), price in self.by_name.items():
                if ra != r:
                    continue
                score = 0
                if n in variants or target == n:
                    score = 100
                elif target in n or n in target:
                    score = 80
                elif len(target) >= 4 and len(n) >= 4 and target[:4] == n[:4]:
                    score = 60
                if score > best_score:
                    best_score = score
                    best = price
            if best_score >= 60:
                return best

        num_key = (*card_num_key(card_number), r)
        return self.by_number.get(num_key, 0)


def fetch_set_kr_prices(collectory_id: str, client: httpx.Client | None = None) -> CollectoryPriceIndex:
    own = client is None
    if own:
        client = httpx.Client(timeout=60, headers={"User-Agent": "Mozilla/5.0"})

    index = CollectoryPriceIndex()
    try:
        res = client.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards")
        res.raise_for_status()
        for card in res.json().get("cards") or []:
            if not is_kr_raw_collectory_card(card):
                continue
            price = int(card.get("price_krw") or 0)
            cid = (card.get("card_id") or "").strip()
            if price <= 0 and not cid:
                continue
            index.add(
                card.get("card_number") or "",
                card.get("name_ko") or card.get("name") or "",
                card.get("rarity") or "",
                price,
                card_id=cid,
            )
    finally:
        if own:
            client.close()
    return index


def lookup_collectory_price(
    index: CollectoryPriceIndex,
    card_number: str,
    name_kr: str,
    rarity: str,
) -> int:
    return index.lookup(card_number, name_kr, rarity)


def _promo_rarity_match(card_rarity: str, target: str) -> bool:
    cr = (card_rarity or "").upper()
    tr = (target or "").upper()
    if cr == tr:
        return True
    if tr in ("P", "PROMO") and cr in ("P", "PROMO", "프로모"):
        return True
    return False


def search_collectory_card_id(
    name_kr: str,
    card_number: str,
    rarity: str,
    client: httpx.Client,
) -> str:
    """collectory 검색 API로 KR 카드 ID 조회 (세트 API 없는 프로모용)."""
    r_upper = (rarity or "P").upper()
    queries = [
        f"{name_kr} {card_number}".strip(),
        f"{card_number} {name_kr}".strip(),
        name_kr,
    ]
    for q in queries:
        if not q:
            continue
        res = client.get(f"{COLLECTORY_API}/cards/search", params={"q": q})
        if res.status_code != 200:
            continue
        for card in res.json().get("results", {}).get("cards") or []:
            if (card.get("region") or "").lower() != "kr":
                continue
            if not _promo_rarity_match(card.get("rarity") or "", r_upper):
                continue
            num = card.get("cardNumber") or card.get("card_number") or ""
            if card_number and num and card_num_key(num) != card_num_key(card_number):
                continue
            cid = (card.get("card_id") or card.get("id") or "").strip()
            if cid:
                return cid
    return ""


def build_collectory_index_from_search(
    cards: list[dict],
    client: httpx.Client,
) -> CollectoryPriceIndex:
    """세트 collectory_id 없을 때 카드별 검색으로 card_id만 채운 인덱스."""
    index = CollectoryPriceIndex()
    for card in cards:
        name_kr = card.get("name_kr") or ""
        card_number = card.get("card_number") or ""
        rarity = card.get("rarity") or "P"
        cid = search_collectory_card_id(name_kr, card_number, rarity, client)
        if cid:
            index.add(card_number, name_kr, rarity, 0, card_id=cid)
    return index


def search_kr_price(
    name_kr: str,
    card_number: str,
    rarity: str,
    client: httpx.Client | None = None,
) -> int:
    """세트 API에 시세가 없을 때 collectory 검색 API로 KR 단일가 조회."""
    own = client is None
    if own:
        client = httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"})

    r_upper = (rarity or "").upper()
    queries = [
        f"{name_kr} {card_number}",
        f"{card_number} {name_kr}",
        name_kr,
    ]
    best = 0
    try:
        for q in queries:
            res = client.get(f"{COLLECTORY_API}/cards/search", params={"q": q})
            if res.status_code != 200:
                continue
            for card in res.json().get("results", {}).get("cards") or []:
                if (card.get("region") or "").lower() != "kr":
                    continue
                if not _promo_rarity_match(card.get("rarity") or "", r_upper):
                    continue
                num = card.get("cardNumber") or card.get("card_number") or ""
                if card_number and num and card_num_key(num) != card_num_key(card_number):
                    continue
                price = int(card.get("price") or card.get("price_krw") or 0)
                if price > 0 and (best == 0 or price < best):
                    best = price
            if best > 0:
                break
    finally:
        if own:
            client.close()
    return best


def lookup_collectory_card_id(
    index: CollectoryPriceIndex,
    card_number: str,
    name_kr: str,
    rarity: str,
) -> str:
    return index.lookup_card_id(card_number, name_kr, rarity)


def fetch_collectory_market_price(card_id: str, client: httpx.Client) -> int:
    """collectory 체결 시세 (collections API, 인증 필요)."""
    sold, _ = fetch_collectory_kr_trades(card_id, client)
    if not sold:
        return 0
    return sold[0] if len(sold) == 1 else sum(sold) // len(sold)


def _collectory_headers() -> dict[str, str]:
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    cookie = os.getenv("COLLECTORY_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie
    return headers


def fetch_collectory_kr_trades(
    card_id: str,
    client: httpx.Client,
) -> tuple[list[int], list[int]]:
    """collectory KR 체결가·호가 분리. (sold_prices, listing_prices)"""
    if not card_id:
        return [], []

    sold: list[int] = []
    listings: list[int] = []
    headers = _collectory_headers()

    try:
        res = client.get(
            f"{COLLECTORY_API}/collections",
            params={"cardId": card_id},
            headers=headers,
            timeout=20,
        )
        if res.status_code == 200:
            for v in res.json().get("variants") or []:
                grade = str(v.get("grade") or v.get("grading") or "Single")
                price = int(v.get("priceKrw") or 0)
                count = int(v.get("count") or 0)
                if price <= 0 or count <= 0:
                    continue
                tier = classify_collectory_row("collectory-market", grade, "")
                if tier is None:
                    continue
                if tier == "sold":
                    sold.append(price)
                else:
                    listings.append(price)
    except Exception:
        pass

    try:
        res = client.get(
            f"{COLLECTORY_API}/collections/sales",
            params={"cardId": card_id},
            headers=headers,
            timeout=20,
        )
        if res.status_code == 200:
            for row in res.json().get("sales") or []:
                source = str(row.get("source") or row.get("platform") or "")
                grade = str(row.get("grade") or row.get("grading") or "Single")
                title = str(row.get("title") or row.get("name") or "")
                tier = classify_collectory_row(source, grade, title)
                price = int(row.get("priceKrw") or row.get("price_krw") or row.get("price") or 0)
                if price <= 0 or tier is None:
                    continue
                if tier == "sold":
                    sold.append(price)
                else:
                    listings.append(price)
    except Exception:
        pass

    return sold, listings


def _normalize_quotes_for_card(quotes: list[PriceQuote], card: dict) -> list[PriceQuote]:
    """공개 거래내역 — 동일 카드 N장은 장당 가격으로, 다종 묶음은 제외."""
    if not card:
        return quotes
    out: list[PriceQuote] = []
    for q in quotes:
        unit = unit_price_from_listing(
            q.price_krw,
            q.title or "",
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            card.get("set_code") or "",
            card.get("set_name_kr") or "",
        )
        if unit is None:
            continue
        out.append(
            PriceQuote(price_krw=unit, tier=q.tier, source=q.source, title=q.title),
        )
    return out


def resolve_market_trades(
    card_id: str,
    client: httpx.Client | None,
    *,
    preloaded_quotes: list[PriceQuote] | None = None,
    use_auth_api: bool = True,
    card: dict | None = None,
) -> tuple[list[int], list[int], list[str], list[str]]:
    """체결·호가 통합 — 인증 API(쿠키 있을 때) + 공개 카드 페이지."""
    sold: list[int] = []
    listings: list[int] = []
    sold_src: list[str] = []
    listing_src: list[str] = []

    cid = (card_id or "").strip()
    if not cid:
        return sold, listings, sold_src, listing_src

    has_cookie = bool(os.getenv("COLLECTORY_COOKIE", "").strip())
    if client is not None and has_cookie and use_auth_api:
        api_sold, api_listings = fetch_collectory_kr_trades(cid, client)
        sold.extend(api_sold)
        listings.extend(api_listings)
        if api_sold:
            sold_src.extend(["collectory"] * len(api_sold))
        if api_listings:
            listing_src.extend(["collectory"] * len(api_listings))

    if preloaded_quotes is not None:
        quotes = preloaded_quotes
    else:
        quotes = fetch_collectory_public_quotes(cid, client)
    if card:
        card_ctx = {
            **card,
            "set_code": card.get("set_code") or "",
            "set_name_kr": card.get("set_name_kr") or "",
        }
        quotes = _normalize_quotes_for_card(quotes, card_ctx)
    pub = public_quotes_to_trades(quotes)
    sold.extend(pub.sold)
    listings.extend(pub.listings)
    sold_src.extend(pub.sold_sources)
    listing_src.extend(pub.listing_sources)

    return sold, listings, sold_src, listing_src


def merge_collectory_primary(
    collectory: int,
    market_prices: list[int],
    *,
    calculate_median_price,
    calculate_trimmed_mean,
    calculate_conservative_price=None,
    rarity: str = "",
    collectory_market: int = 0,
    sold_prices: list[int] | None = None,
    listing_prices: list[int] | None = None,
    sold_sources: list[str] | None = None,
    listing_sources: list[str] | None = None,
) -> tuple[int, int, int, str]:
    """체결 → 호가 → 미등록. collectory set API 최저가(collectory 인자)는 사용하지 않음."""
    from lib.price_resolve import resolve_tiered_price

    sold: list[int] = list(sold_prices or [])
    listings: list[int] = list(listing_prices or [])

    if collectory_market > 0:
        sold.append(collectory_market)

    listings.extend(p for p in market_prices if p > 0)

    sold_src = list(sold_sources or [])
    if sold and not sold_src:
        sold_src = ["collectory"] * len(sold)
    listing_src = list(listing_sources or [])
    if market_prices and not listing_src:
        listing_src = ["bunjang"] * len(market_prices)

    return resolve_tiered_price(
        sold,
        listings,
        rarity,
        calculate_median_price=calculate_median_price,
        calculate_trimmed_mean=calculate_trimmed_mean,
        calculate_conservative_price=calculate_conservative_price or calculate_median_price,
        sold_sources=sold_src,
        listing_sources=listing_src,
    )
