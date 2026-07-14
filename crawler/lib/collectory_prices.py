"""collectory.cc 한글판 시세 조회 (미등급·KR 검증)."""
from __future__ import annotations

import re

import httpx

COLLECTORY_API = "https://collectory.cc/api"


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

    def add(self, card_number: str, name_ko: str, rarity: str, price: int) -> None:
        r = (rarity or "").upper()
        num_key = (*card_num_key(card_number), r)
        name_key = (norm_name(name_ko), r)
        if num_key not in self.by_number or price < self.by_number[num_key]:
            self.by_number[num_key] = price
        if name_key not in self.by_name or price < self.by_name[name_key]:
            self.by_name[name_key] = price

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
            if price <= 0:
                continue
            index.add(
                card.get("card_number") or "",
                card.get("name_ko") or card.get("name") or "",
                card.get("rarity") or "",
                price,
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
                if (card.get("rarity") or "").upper() != r_upper:
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


def merge_collectory_primary(
    collectory: int,
    market_prices: list[int],
    *,
    calculate_median_price,
) -> tuple[int, int, int, str]:
    """collectory 1차 + 번개장터·기타 마켓 보조 중앙값."""
    market = [p for p in market_prices if p > 0]

    if collectory > 0 and market:
        pool = [collectory, collectory, *market]
        median = calculate_median_price(pool)
        low = min(collectory, min(market))
        return median, low, 1 + len(market), "collectory+bunjang"

    if collectory > 0:
        return collectory, collectory, 1, "collectory"

    if market:
        median = calculate_median_price(market)
        return median, min(market), len(market), "bunjang"

    return 0, 0, 0, "none"
