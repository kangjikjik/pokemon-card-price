"""일본판 raw 싱글 — 번개·크림·Collectory 거래내역 검색·필터."""
from __future__ import annotations

import re

from lib.price_search import (
    BUY_KEYWORDS,
    CARD_NUMBER_RE,
    GRADED_KEYWORDS,
    JP_KEYWORDS,
    KR_KEYWORDS,
    RARITY_BLOCK_ABOVE,
    RARITY_TOKENS,
    SET_CODE_ALIASES,
    calculate_median_price,
)

# Collectory JP rarity mismatch (MUR ↔ UR 등)
JP_RARITY_EQUIV: dict[str, set[str]] = {
    "MUR": {"MUR", "UR", "メガウルトラ", "MEGAULTRA"},
    "SAR": {"SAR", "SR", "スペシャルアート"},
    "SR": {"SR", "スーパーレア"},
    "AR": {"AR", "アートレア"},
    "RR": {"RR", "ダブルレア"},
    "P": {"P", "PROMO", "プロモ"},
}

BUNJANG_JP_HINTS = [
    "일본", "일판", "일어", "JP", "jp", "日本", "japanese", "영문판", "미판",
    "Japanese", "海外", "일본산", "일본발",
]


def build_jp_search_queries(
    set_name_kr: str,
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    *,
    slim: bool = False,
) -> list[str]:
    """번개장터 일본판 검색어.

    slim=True: 구형/희박 팩은 핵심 쿼리 3개만 사용.
    """
    r = (rarity or "").upper()
    num = (card_number or "").strip()
    num_short = num.split("/")[0] if num else ""
    jp = (name_jp or name_kr or "").strip()
    kr = (name_kr or "").strip()
    code = (set_code or "").upper()

    queries: list[str] = []
    if jp and r:
        queries.append(f"포켓몬카드 {jp} {r} 일본")
        queries.append(f"포켓몬카드 {jp} {r} 일판")
    if kr and r:
        queries.append(f"포켓몬카드 {kr} {r} 일판")

    if not slim:
        if kr and r:
            queries.append(f"포켓몬카드 {kr} {r} 일본")
        if code and jp and r:
            queries.append(f"포켓몬카드 {code} {jp} {r}")
        if code and kr and r:
            queries.append(f"포켓몬카드 {code} {kr} {r} 일판")
        if num and jp and r:
            queries.append(f"포켓몬카드 {num} {jp} {r}")
        if num and kr and r:
            queries.append(f"포켓몬카드 {num} {kr} {r} 일판")
        if set_name_kr and jp:
            queries.append(f"포켓몬카드 {set_name_kr} {jp} {r}".strip())
        for alias in SET_CODE_ALIASES.get(code, []):
            if jp:
                queries.append(f"포켓몬카드 {alias} {jp} {r}")

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _is_korean_listing(title: str) -> bool:
    if any(k in title for k in KR_KEYWORDS):
        return True
    if "한글" in title or "한국판" in title:
        return True
    return False


def _is_graded_listing(title: str) -> bool:
    t = title.upper()
    return any(k.upper() in t for k in GRADED_KEYWORDS)


def _title_matches_jp_name(title: str, name_jp: str, name_kr: str) -> bool:
    for name in (name_jp, name_kr):
        n = (name or "").strip()
        if not n:
            continue
        core = n
        for suf in [" ex", " EX", " VSTAR", " VMAX", " V", " GX"]:
            if core.endswith(suf):
                core = core[: -len(suf)].strip()
                break
        if len(core) >= 2 and (core in title or n in title):
            return True
        if len(n) >= 3 and n[:3] in title:
            return True
    return False


def _title_matches_jp_rarity(title: str, rarity: str) -> bool:
    r = (rarity or "").upper()
    t = title.upper()
    equiv = JP_RARITY_EQUIV.get(r, {r})
    tokens: set[str] = set()
    for eq in equiv:
        tokens.update(RARITY_TOKENS.get(eq, [eq]))
        tokens.add(eq)
    has = any(tok.upper() in t for tok in tokens if tok)
    if r == "RR" and not has:
        for block in RARITY_BLOCK_ABOVE.get("RR", []):
            for bt in RARITY_TOKENS.get(block, [block]):
                if bt.upper() in t:
                    return False
        return True
    if not has and r in ("SR", "SAR", "AR", "MUR", "UR"):
        return False
    return True


def _is_bundle_listing(title: str) -> bool:
    if re.search(r"\d{3}/\d{3}.*\d{3}/\d{3}", title):
        return True
    for kw in ("박스", "팩 ", "팩,", "덱", "세트", "묶음", "일괄", "다량", "대량"):
        if kw in title:
            return True
    return False


def is_raw_jp_listing(
    title: str,
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
) -> bool:
    """일본판 raw 싱글 (번개·크림 호가)."""
    if not title.strip():
        return False
    if any(k in title for k in BUY_KEYWORDS):
        return False
    if _is_graded_listing(title):
        return False
    if _is_korean_listing(title):
        return False
    if _is_bundle_listing(title):
        return False
    if not _title_matches_jp_name(title, name_jp, name_kr):
        return False
    if not _title_matches_jp_rarity(title, rarity):
        return False
    # 일본판 힌트 없으면 제외 (한글판 오염 방지)
    if not any(h in title for h in BUNJANG_JP_HINTS):
        # 카드번호만으로 일본판 판별 (151 201/165 일본 등)
        if card_number and card_number in title:
            pass
        else:
            return False
    num = (card_number or "").strip()
    if num:
        matches = CARD_NUMBER_RE.findall(title)
        if matches and num not in matches:
            return False
    return True


def filter_bunjang_jp_listings(
    items: list[dict],
    name_jp: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
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
        if not is_raw_jp_listing(title, name_jp, name_kr, rarity, card_number):
            continue
        prices.append(price)
    return prices


def resolve_jp_tiered_price(
    sold: list[int],
    listings: list[int],
    *,
    calculate_median_price_fn=calculate_median_price,
) -> tuple[int, int, str]:
    """체결(메ルカ리·SNKRDUNK·카페) → 번개·크림 호가 → 미등록."""
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
