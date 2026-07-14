"""등급별 시세 검색 키워드·리스팅 필터 (미등급·한글판 위주)."""
from __future__ import annotations

import re

# 검색 시 상위 등급 오염 방지 (SR 검색 시 SAR/MUR 제외)
RARITY_BLOCK_ABOVE: dict[str, list[str]] = {
    "AR": ["SAR", "SR", "MUR", "UR", "HR", "SSR", "CSR"],
    "SR": ["SAR", "MUR", "UR", "HR", "SSR"],
    "SAR": ["MUR", "UR"],
    "CSR": ["SAR", "MUR"],
    "CHR": ["SAR", "MUR"],
    "PR": ["SAR", "MUR", "UR"],
    "TR": ["SAR", "MUR"],
    "RRR": ["SAR", "MUR"],
    "ACE": ["SAR", "MUR"],
    "UR": ["MUR"],
    "HR": ["MUR"],
    "SSR": ["MUR"],
}

RARITY_TOKENS: dict[str, list[str]] = {
    "MUR": ["MUR", "무르", "메가울트라", "메가 울트라"],
    "SAR": ["SAR", "사르", "스페셜아트", "스페셜 아트"],
    "SR": ["SR", "슈퍼레어", "슈퍼 레어"],
    "AR": ["AR", "아트레어", "아트 레어"],
    "UR": ["UR", "울트라레어", "울트라 레어"],
    "ACE": ["ACE", "에이스", "에이스스펙"],
    "HR": ["HR", "하이퍼레어"],
    "SSR": ["SSR", "샤이닝슈퍼"],
    "CSR": ["CSR", "캐릭터슈퍼"],
    "CHR": ["CHR", "캐릭터레어"],
    "PR": ["PR", "프리즘"],
    "TR": ["TR", "트레이너스레어"],
    "RRR": ["RRR", "트리플레어"],
    "BWR": ["BWR"],
    "MA": ["MA", "메가어택"],
    "FUR": ["FUR"],
}

CARD_NUMBER_RE = re.compile(r"\b(\d{1,3}/\d{1,3})\b")

# PSA·BGS 등 등급(슬랩) 카드 제외
GRADED_KEYWORDS = [
    "PSA", "BGS", "CGC", "SGC", "ARS", "GRAAD", "PCG", "HGA", "KSA",
    "슬랩", "slab", "SLAB", "등급", "감정", "실물감정", "채점",
    "GEM", "gem", "10점", "9.5", "mint10", "MINT10", "NM10",
    "ss급", "SS급",
]

# 일본/해외판 (한글판 표기 없으면 제외)
JP_KEYWORDS = [
    "일판", "일본", "일어", "JP", "jp", "日本", "japanese", "영문판", "영판", "미판",
    "English", "EN ", " EN", "海外",
]

KR_KEYWORDS = [
    "한글", "한국", "국내", "한글판", "한판", "KR", "kr", "Korean", "코리안",
    "한국)", "한국판",
]

BUNDLE_KEYWORDS = [
    "박스", "팩", "덱", "앨범", "바인더", "슬리브", "다량", "대량", "통판",
    "일괄", "묶음", "세트", "SET", "set", "종 ", "종(", "종세트",
    "2종", "3종", "4종", "5종", "6종", "7종", "8종", "9종", "10종",
    "2장", "3장", "4장", "5장", "6장", "7장", "8장", "9장", "10장",
    "장세트", "장 팝", "장팝", "장판",
]

SET_CODE_ALIASES: dict[str, list[str]] = {
    "MG6": ["MG6", "M5", "m5", "어비스아이", "어비스 아이"],
}


def build_search_queries(
    set_name_kr: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
) -> list[str]:
    """등급·세트·카드번호·한글판을 포함한 검색어 목록."""
    base = name_kr.strip()
    num = card_number.strip()
    num_short = num.split("/")[0] if num else ""
    r = rarity.upper()
    code = set_code.strip().upper()

    queries: list[str] = []
    if set_name_kr and base and r:
        queries.append(f"포켓몬카드 {set_name_kr} {base} {r} 한글")
        queries.append(f"포켓몬카드 {set_name_kr} {base} {r}")
    if code and base and r:
        queries.append(f"포켓몬카드 {code} {base} {r}")
    if set_name_kr and base and num:
        queries.append(f"포켓몬카드 {set_name_kr} {base} {num}")
    if base and r:
        queries.append(f"포켓몬카드 {base} {r} {set_name_kr}".strip())
    if set_name_kr and base:
        queries.append(f"포켓몬카드 {set_name_kr} {base}")
    if num_short and r and set_name_kr:
        queries.append(f"포켓몬카드 {set_name_kr} {num_short} {r}")
    if set_name_kr and num and r:
        queries.append(f"포켓몬카드 {set_name_kr} {num} {r}")

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _title_matches_rarity(title: str, rarity: str) -> bool:
    t = title.upper()
    r = rarity.upper()
    tokens = RARITY_TOKENS.get(r, [r])
    if not any(tok.upper() in t for tok in tokens):
        if r in ("SR", "SAR", "AR", "MUR", "UR", "ACE"):
            return False
        return True
    for block in RARITY_BLOCK_ABOVE.get(r, []):
        for bt in RARITY_TOKENS.get(block, [block]):
            if bt.upper() in t:
                return False
    return True


def _title_matches_name(title: str, name_kr: str) -> bool:
    name = name_kr.strip()
    if not name:
        return True
    core = name
    for suf in [" ex", " EX", " VSTAR", " VMAX", " V", " GX"]:
        if core.endswith(suf):
            core = core[: -len(suf)].strip()
            break
    if len(core) >= 2 and core in title:
        return True
    if name in title:
        return True
    return False


def _is_japanese_listing(title: str) -> bool:
    t = title
    if any(k in t for k in KR_KEYWORDS):
        return False
    return any(k in t for k in JP_KEYWORDS)


def _is_graded_listing(title: str) -> bool:
    t = title.upper()
    return any(k.upper() in t for k in GRADED_KEYWORDS)


def _is_bundle_listing(title: str, name_kr: str) -> bool:
    if any(k in title for k in BUNDLE_KEYWORDS):
        return True
    if re.search(r"\d{3}/\d{3}.*\d{3}/\d{3}", title):
        return True
    # 콤마/플러스로 여러 카드명 나열 (단품 아님)
    if re.search(r"[,+·/]", title):
        parts = re.split(r"[,+·]", title)
        name_hits = sum(1 for p in parts if name_kr[:2] in p or (len(name_kr) >= 3 and name_kr in p))
        if len(parts) >= 2 and name_hits <= 1:
            other_names = sum(
                1 for p in parts
                if len(p.strip()) >= 3 and name_kr not in p and not re.search(r"\d{3}/\d{3}", p)
            )
            if other_names >= 1:
                return True
    return False


def is_raw_kr_listing(
    title: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    set_name_kr: str = "",
) -> bool:
    """미등급·한글판 단품 매물인지 판별."""
    if not title.strip():
        return False
    if _is_graded_listing(title):
        return False
    if _is_japanese_listing(title):
        return False
    if _is_bundle_listing(title, name_kr):
        return False
    if not _title_matches_name(title, name_kr):
        return False
    if not _title_matches_rarity(title, rarity):
        return False

    num = card_number.strip()
    if num:
        matches = CARD_NUMBER_RE.findall(title)
        if matches and num not in matches:
            return False

    return True


def filter_bunjang_listings(
    items: list[dict],
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    set_name_kr: str = "",
) -> list[int]:
    """번개장터 리스팅에서 미등급 한글판 단품 가격만 추출."""
    prices: list[int] = []

    for item in items:
        title = str(item.get("name", ""))
        try:
            price = int(item.get("price", 0) or 0)
        except (TypeError, ValueError):
            continue
        if price < 300 or price > 5_000_000:
            continue
        if not is_raw_kr_listing(title, name_kr, rarity, card_number, set_code, set_name_kr):
            continue
        prices.append(price)
    return prices


def filter_prices_by_rarity_band(prices: list[int], rarity: str) -> list[int]:
    """등급별 대략적 가격 밴드 (한글판 미등급 기준)."""
    if not prices:
        return prices
    bands: dict[str, tuple[int, int]] = {
        "AR": (300, 3_500),
        "SR": (500, 80_000),
        "SAR": (3_000, 250_000),
        "MUR": (30_000, 800_000),
        "UR": (3_000, 200_000),
        "ACE": (5_000, 150_000),
        "HR": (3_000, 150_000),
        "SSR": (5_000, 150_000),
    }
    lo, hi = bands.get(rarity.upper(), (300, 3_000_000))
    filtered = [p for p in prices if lo <= p <= hi]
    return filtered if filtered else prices


def calculate_median_price(prices: list[int]) -> int:
    """중앙값 (저가 쏠림 시세에 적합)."""
    if not prices:
        return 0
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    mid = n // 2
    if n % 2:
        return sorted_prices[mid]
    return (sorted_prices[mid - 1] + sorted_prices[mid]) // 2


def calculate_min_price(prices: list[int]) -> int:
    return min(prices) if prices else 0


def calculate_representative_price(prices: list[int]) -> int:
    """대표 시세 = 중앙값."""
    return calculate_median_price(prices)


# 하위 호환
def calculate_average(prices: list[int]) -> int:
    return calculate_representative_price(prices)
