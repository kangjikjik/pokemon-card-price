"""
시세 정책 — 체결가 우선, 호가 최저가 fallback, 미등록.

1. 한글판 raw 싱글만 (PSA/BRG/일판/묶음 제외)
2. 체결 있으면 중앙값/절사평균 등급별 대표 시세
3. 체결 없으면 호가 fallback — 번개 우선, 쇼핑몰 25% 할인, SAR+ 중앙값
4. 체결·호가 모두 없으면 미등록
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# 호가 fallback — 출처별 보정·우선순위
NAVER_SHOPPING_ADJUST = 0.75  # 쇼핑몰 호가 25% 할인 후 비교
LISTING_HIGH_TIER_MEDIAN = frozenset({"SAR", "MUR", "MA", "UR", "ACE", "HR", "SSR", "P", "PROMO"})

LISTING_SOURCE_PRIORITY: dict[str, int] = {
    "bunjang": 1,
    "번개장터": 1,
    "tcgbox": 2,
    "TCGBox": 2,
    "kream": 2,
    "킨들샵": 2,
    "yuyutei": 2,
    "유유테이": 2,
    "break": 2,
    "naver_shopping": 3,
    "네이버쇼핑": 3,
    "collectory-floor": 3,
    "unknown": 4,
}

# collectory JP 거래 출처 — 체결(메ルカ리·SNKRDUNK·카페 등)
JP_SOLD_SOURCES = frozenset({
    "mercari",
    "メルカリ",
    "snkrdunk",
    "SNKRDUNK",
    "naver_cafe",
    "네이버카페",
    "break",
    "Break",
    "cardmvk",
})

# JP 호가 — 번개·크림·쇼핑
JP_LISTING_SOURCES = frozenset({
    "bunjang",
    "번개장터",
    "kream",
    "킨들샵",
    "KREAM",
    "naver_shopping",
    "네이버쇼핑",
    "tcgbox",
    "TCGBox",
})

# collectory KR 거래 출처 — 체결(카페 마감·Break 등)
SOLD_SOURCES = frozenset({
    "naver_cafe",
    "네이버카페",
    "break",
    "Break",
    "BREAK",
    "cardmvk",
})

# 쇼핑몰·카드샵·번개 호가
LISTING_SOURCES = frozenset({
    "naver_shopping",
    "네이버쇼핑",
    "tcgbox",
    "TCGBox",
    "cardnyang",
    "카드냥",
    "킨들샵",
    "kream",
    "collectory-floor",
    "bunjang",
    "번개장터",
})

# 등급(슬랩) 표기 — raw 싱글 제외
GRADED_GRADE_TOKENS = frozenset({
    "PSA", "BGS", "CGC", "SGC", "ARS", "BRG", "GRAAD", "PCG", "HGA", "KSA",
    "GEM", "MINT", "NM10", "10점", "9.5",
})

# SNKRDUNK 등 하자·저상태 — raw 싱글 시세로 쓰지 않음
DAMAGED_GRADE_TOKENS = frozenset({
    "D", "E", "F", "D급", "E급", "F급", "하자", "키즈", "KIDS", "傷", "傷あり", "傷有",
})


@dataclass(frozen=True)
class PriceQuote:
    price_krw: int
    tier: str  # sold | listing
    source: str
    title: str = ""
    url: str = ""           # SNKRDUNK·메ルカリ 등 원본 링크
    trade_date: str = ""    # Collectory 표시일 → ISO YYYY-MM-DD


def is_damaged_grade(grade: str) -> bool:
    g = (grade or "").strip()
    if not g:
        return False
    gu = g.upper()
    if gu in ("D", "E", "F") or g in ("D급", "E급", "F급"):
        return True
    return any(tok in g for tok in DAMAGED_GRADE_TOKENS)


def is_graded_grade(grade: str) -> bool:
    if is_damaged_grade(grade):
        return True
    g = (grade or "").strip().upper()
    if not g or g in ("SINGLE", "RAW", "S", "A", "B", "C", "S급", "A급", "B급", "C급"):
        return False
    if g.startswith("BRG") or g.startswith("PSA") or g.startswith("BGS"):
        return True
    return any(tok in g for tok in GRADED_GRADE_TOKENS)


def classify_collectory_row(source: str, grade: str, title: str) -> str | None:
    """체결/호가 분류. 등급 카드면 None."""
    if is_graded_grade(grade):
        return None
    src = (source or "").strip()
    src_lower = src.lower()
    if any(s.lower() in src_lower for s in SOLD_SOURCES):
        return "sold"
    if any(s.lower() in src_lower for s in LISTING_SOURCES):
        return "listing"
    # 알 수 없는 출처 — 제목에 등급 키워드 있으면 제외
    t = (title or "").upper()
    if any(k in t for k in ("PSA", "BRG", "BGS", "CGC", "슬랩", "일판", "JP ", "영문판")):
        return None
    return "listing"


def classify_collectory_row_jp(source: str, grade: str, title: str) -> str | None:
    """일본판 — 메ルカ리·SNKRDUNK·카페=체결, 번개·크림=호가."""
    if is_graded_grade(grade):
        return None
    src = (source or "").strip()
    src_lower = src.lower()
    if any(s.lower() in src_lower for s in JP_SOLD_SOURCES):
        return "sold"
    if any(s.lower() in src_lower for s in JP_LISTING_SOURCES):
        return "listing"
    t = (title or "").upper()
    if any(k in t for k in ("PSA", "BRG", "BGS", "CGC", "슬랩")):
        return None
    return "sold"


def allows_listing_fallback(rarity: str) -> bool:
    """체결 없을 때 호가 fallback 허용 (모든 등급)."""
    return True


def _listing_priority(source: str) -> int:
    s = (source or "").strip().lower()
    for key, pri in LISTING_SOURCE_PRIORITY.items():
        if key.lower() in s or s == key.lower():
            return pri
    return LISTING_SOURCE_PRIORITY["unknown"]


def _adjusted_listing_price(price: int, source: str) -> int:
    src = (source or "").lower()
    if "naver_shopping" in src or "네이버쇼핑" in (source or ""):
        return max(100, int(price * NAVER_SHOPPING_ADJUST))
    return price


def resolve_listing_price(
    listings: list[int],
    sources: list[str],
    rarity: str,
    *,
    calculate_median_price: Callable[[list[int]], int],
    calculate_trimmed_mean: Callable[[list[int]], int],
) -> tuple[int, int]:
    """호가 fallback. 번개 우선·쇼핑몰 할인·SAR+ 중앙값."""
    if not listings:
        return 0, 0

    srcs = sources if len(sources) == len(listings) else ["bunjang"] * len(listings)
    pairs = [
        (_adjusted_listing_price(p, s), p, s)
        for p, s in zip(listings, srcs)
        if p > 0
    ]
    if not pairs:
        return 0, 0

    r = (rarity or "").upper()
    adjusted = [a for a, _, _ in pairs]
    has_bunjang = any(_listing_priority(s) == 1 for _, _, s in pairs)

    if r in LISTING_HIGH_TIER_MEDIAN and len(adjusted) >= 2:
        bj = [a for a, _, s in pairs if _listing_priority(s) == 1]
        if bj and len(bj) >= 2:
            price = calculate_trimmed_mean(bj) if len(bj) >= 3 else calculate_median_price(bj)
            return price, min(bj)
        if not has_bunjang:
            price = calculate_trimmed_mean(adjusted) if len(adjusted) >= 3 else calculate_median_price(adjusted)
            return price, min(adjusted)

    best_pri = min(_listing_priority(s) for _, _, s in pairs)
    tier = [a for a, _, s in pairs if _listing_priority(s) == best_pri]
    if r in ("P", "PROMO") and len(tier) >= 2:
        price = calculate_trimmed_mean(tier) if len(tier) >= 3 else calculate_median_price(tier)
        return price, min(tier)
    price = min(tier)
    return price, price


def aggregate_prices(
    prices: list[int],
    rarity: str,
    *,
    calculate_median_price: Callable[[list[int]], int],
    calculate_trimmed_mean: Callable[[list[int]], int],
    calculate_conservative_price: Callable[[list[int]], int],
) -> int:
    if not prices:
        return 0
    r = (rarity or "").upper()
    if r == "RR":
        return calculate_conservative_price(prices) if len(prices) >= 4 else calculate_median_price(prices)
    if r in {"SR", "SAR", "MUR", "MA", "UR", "ACE", "HR", "SSR", "CSR", "CHR", "PR", "TR", "RRR", "BWR", "FUR"}:
        return calculate_trimmed_mean(prices) if len(prices) >= 3 else calculate_median_price(prices)
    return calculate_median_price(prices)


def resolve_tiered_price(
    sold: list[int],
    listings: list[int],
    rarity: str,
    *,
    calculate_median_price: Callable[[list[int]], int],
    calculate_trimmed_mean: Callable[[list[int]], int],
    calculate_conservative_price: Callable[[list[int]], int],
    sold_sources: list[str] | None = None,
    listing_sources: list[str] | None = None,
) -> tuple[int, int, int, str]:
    """체결 → 호가 최저가 → 미등록."""
    sold = [p for p in sold if p > 0]
    listings = [p for p in listings if p > 0]

    if sold:
        pool = sold
        price = aggregate_prices(
            pool, rarity,
            calculate_median_price=calculate_median_price,
            calculate_trimmed_mean=calculate_trimmed_mean,
            calculate_conservative_price=calculate_conservative_price,
        )
        src = "sold:" + "+".join(dict.fromkeys(sold_sources or ["market"]))
        return price, min(pool), len(pool), src

    if listings:
        srcs = listing_sources if listing_sources and len(listing_sources) == len(listings) else None
        if not srcs:
            srcs = ["bunjang"] * len(listings)
        price, low = resolve_listing_price(
            listings,
            srcs,
            rarity,
            calculate_median_price=calculate_median_price,
            calculate_trimmed_mean=calculate_trimmed_mean,
        )
        if price > 0:
            src = "listing:" + "+".join(dict.fromkeys(srcs or ["bunjang"]))
            return price, low, len(listings), src

    return 0, 0, 0, "none"
