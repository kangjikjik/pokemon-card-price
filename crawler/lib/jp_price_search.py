"""일본판 raw 싱글 — 번개·크림·Collectory 거래내역 검색·필터."""
from __future__ import annotations

import re

from lib.bunjang_market_names import (
    build_bunjang_jp_queries,
    fix_display_name_kr,
    title_matches_bunjang_name,
)
from lib.price_search import (
    BUY_KEYWORDS,
    CARD_NUMBER_RE,
    GRADED_KEYWORDS,
    KR_KEYWORDS,
    RARITY_BLOCK_ABOVE,
    RARITY_TOKENS,
    _is_goods_listing,
    _is_multi_card_sale,
    calculate_median_price,
    card_number_in_title,
    title_has_commemorative_year,
    title_has_sl_reprint,
)

JP_RARITY_EQUIV: dict[str, set[str]] = {
    "MUR": {"MUR", "UR", "メガウルトラ", "MEGAULTRA"},
    "SAR": {"SAR", "SR", "スペシャルアート"},
    "SR": {"SR", "スーパーレア"},
    "AR": {"AR", "アートレア"},
    "RR": {"RR", "ダブルレア"},
    "P": {"P", "PROMO", "プロモ"},
}

BUNJANG_JP_HINTS = [
    "일본", "일판", "일어", "일어판", "JP", "jp", "日本", "japanese", "영문판", "미판",
    "Japanese", "海外", "일본산", "일본발",
]


def filter_jp_items_by_kr_floor(items: list[dict], kr_reference: int) -> list[dict]:
    """일본판 가격이 한국판 대표 시세보다 낮으면 오매칭으로 제외."""
    if kr_reference <= 0:
        return items
    return [it for it in items if int(it.get("price", 0) or 0) >= kr_reference]


def filter_jp_prices_by_kr_floor(prices: list[int], kr_reference: int) -> list[int]:
    if kr_reference <= 0:
        return prices
    return [p for p in prices if p >= kr_reference]


def build_jp_search_queries(
    set_name_kr: str,
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    *,
    slim: bool = False,
    name_en: str = "",
) -> list[str]:
    """번개장터 일판 검색어 — 한글 시장 표기만 (일본어 금지)."""
    return build_bunjang_jp_queries(
        set_name_kr,
        name_kr,
        name_jp,
        rarity,
        card_number,
        set_code,
        name_en=name_en,
        slim=slim,
    )


def _explicit_kr_title(title: str) -> bool:
    """한국판·한글판 등 명시 표기."""
    if any(k in title for k in KR_KEYWORDS):
        return True
    if "한글" in title or "한국판" in title or "한글판" in title:
        return True
    if "한국)" in title or title.strip().startswith("한국"):
        return True
    return False


def _is_korean_listing(title: str, *, allow_ambiguous_jp: bool = False) -> bool:
    """번개 기본은 국내 매물 — 일판·일본 표기 없으면 한국판으로 간주."""
    if _explicit_kr_title(title):
        return True
    if allow_ambiguous_jp:
        return False
    if not any(h in title for h in BUNJANG_JP_HINTS):
        return True
    return False


def _is_graded_listing(title: str) -> bool:
    t = title.upper()
    return any(k.upper() in t for k in GRADED_KEYWORDS)


def _title_matches_jp_rarity(title: str, rarity: str, set_code: str = "") -> bool:
    from lib.price_search import is_cel30_sl  # noqa: PLC0415

    if is_cel30_sl(set_code, rarity):
        return True
    r = (rarity or "").upper()
    t = title.upper()
    equiv = JP_RARITY_EQUIV.get(r, {r})
    tokens: set[str] = set()
    for eq in equiv:
        tokens.update(RARITY_TOKENS.get(eq, [eq]))
        tokens.add(eq)
    has = any(tok.upper() in t for tok in tokens if tok)
    if r == "RR":
        for block in RARITY_BLOCK_ABOVE.get("RR", []):
            for bt in RARITY_TOKENS.get(block, [block]):
                if bt.upper() in t:
                    return False
        if not has:
            return " RR" in f" {title.upper()} " or title.upper().startswith("RR ")
        return True
    if not has and r in ("SR", "SAR", "AR", "MUR", "UR"):
        return False
    return True


def _is_bundle_listing(title: str) -> bool:
    if re.search(r"\d{3}/\d{3}.*\d{3}/\d{3}", title):
        return True
    if "덱소스" in title or "덱 소스" in title:
        pass
    elif "덱" in title:
        return True
    for kw in ("박스", "팩 ", "팩,", "세트", "묶음", "일괄", "다량", "대량"):
        if kw in title:
            return True
    if title.count(" EX ") + title.count(" RR ") + title.count(" SAR ") >= 2:
        if any(k in title for k in ("판매합니다", "팝니다", "일괄", "세트")):
            return True
    return False


def is_raw_jp_listing(
    title: str,
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    *,
    name_en: str = "",
    set_code: str = "",
) -> bool:
    """일본판 raw 싱글 (번개)."""
    if not title.strip():
        return False
    if any(k in title for k in BUY_KEYWORDS):
        return False
    if _is_goods_listing(title):
        return False
    if _is_graded_listing(title):
        return False
    from lib.trainer_item_cards import skip_card_number_in_title  # noqa: PLC0415

    is_trainer_item = skip_card_number_in_title(set_code, card_number, name_jp)
    if _is_korean_listing(title, allow_ambiguous_jp=is_trainer_item):
        return False
    if not title_has_commemorative_year(title, set_code):
        return False
    if not title_has_sl_reprint(title, rarity):
        return False
    if _is_bundle_listing(title):
        return False
    if _is_multi_card_sale(title, fix_display_name_kr(name_kr)):
        return False
    if not title_matches_bunjang_name(
        title, name_kr, name_jp, name_en, rarity, card_number, set_code
    ):
        return False
    if not _title_matches_jp_rarity(title, rarity, set_code):
        return False
    # 포켓몬 ex: 일판 표기 필수. 트레이너·아이템은 체결 제목에 일판이 없는 경우가 많음.
    if not is_trainer_item and not any(h in title for h in BUNJANG_JP_HINTS):
        return False

    num = (card_number or "").strip()
    if num and not skip_card_number_in_title(set_code, card_number, name_jp):
        if not card_number_in_title(title, num):
            return False
    return True


def filter_bunjang_jp_listings(
    items: list[dict],
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    **kwargs,
) -> list[int]:
    prices: list[int] = []
    for item in items:
        title = str(item.get("name", ""))
        try:
            price = int(item.get("price", 0) or 0)
        except (TypeError, ValueError):
            continue
        if price < 500 or price > 10_000_000:
            continue
        if not is_raw_jp_listing(
            title, name_jp, fix_display_name_kr(name_kr), rarity, card_number, **kwargs
        ):
            continue
        prices.append(price)
    return prices


def resolve_jp_tiered_price(
    sold: list[int],
    listings: list[int],
    *,
    calculate_median_price_fn=calculate_median_price,
) -> tuple[int, int, str]:
    from lib.price_resolve import aggregate_prices, resolve_listing_price

    sold = [p for p in sold if p > 0]
    listings = [p for p in listings if p > 0]
    if sold:
        price = aggregate_prices(
            sold,
            "SAR",
            calculate_median_price=calculate_median_price_fn,
            calculate_trimmed_mean=calculate_median_price_fn,
            calculate_conservative_price=calculate_median_price_fn,
        )
        return price, len(sold), "sold:collectory"
    if listings:
        price, _ = resolve_listing_price(
            listings,
            ["bunjang"] * len(listings),
            "SAR",
            calculate_median_price=calculate_median_price_fn,
            calculate_trimmed_mean=calculate_median_price_fn,
        )
        if price > 0:
            return price, len(listings), "listing:bunjang+kream"
    return 0, 0, "none"
