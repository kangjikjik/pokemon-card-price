"""등급별 시세 검색 키워드·리스팅 필터 (미등급·한글판 위주)."""
from __future__ import annotations

import re

# 검색 시 상위 등급 오염 방지 (SR 검색 시 SAR/MUR 제외)
RARITY_BLOCK_ABOVE: dict[str, list[str]] = {
    "RR": ["AR", "SR", "SAR", "MUR", "UR", "HR", "SSR", "CSR", "CHR", "ACE", "RRR", "PR", "TR"],
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
    "RR": ["RR", "더블레어", "더블 레어", "더블"],
    "P": ["P", "프로모", "PROMO", "프로모션"],
    "BWR": ["BWR"],
    "MA": ["MA", "메가어택"],
    "FUR": ["FUR"],
}

CARD_NUMBER_RE = re.compile(r"\b(\d{1,3}/\d{1,3})\b")

# PSA·BGS·BRG 등 등급(슬랩) 카드 제외
GRADED_KEYWORDS = [
    "PSA", "BGS", "CGC", "SGC", "ARS", "GRAAD", "PCG", "HGA", "KSA", "BRG",
    "슬랩", "slab", "SLAB", "등급", "감정", "실물감정", "채점", "그레이딩",
    "GEM", "gem", "10점", "9.5", "mint10", "MINT10", "NM10",
    "ss급", "SS급", "brg10", "brg9", "brg8", "psa10", "psa9",
]

# 일본/해외판 (한글판 표기 없으면 제외)
JP_KEYWORDS = [
    "일본판", "일판", "일본", "일어", "JP", "jp", "日本", "japanese", "영문판", "영판", "미판",
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
    "장세트", "장 팝", "장팝", "장판",
]

# 매입·구매글 (판매 호가 아님)
BUY_KEYWORDS = [
    "매입", "구매해", "삽니다", "구매)", "구매]", "buying", "삽니다",
    "대량매입", "매입)", "매입]", "구매 잉", "구매해요",
]

PROMO_MP_NUMBER_RE = re.compile(r"\d{2,3}/M-P", re.I)

# 동일 카드 N장 — 장당 환산 (제외하지 않음)
QUANTITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(\d{1,2})\s*장(?!\s*(?:세트|판|팝|식))"),
    re.compile(r"(\d{1,2})\s*매"),
    re.compile(r"(\d{1,2})\s*개"),
    re.compile(r"[xX×]\s*(\d{1,2})"),
    re.compile(r"(\d{1,2})\s*[xX×](?!\d)"),
]

MAX_SINGLE_LISTING_QTY = 20

SET_CODE_ALIASES: dict[str, list[str]] = {
    "MG7": ["MG7", "M6", "m6", "스톰에메랄다", "스톰 에메랄다"],
    "MG6": ["MG6", "M5", "m5", "어비스아이", "어비스 아이"],
    "MG5": ["MG5", "니힐제로", "니힐 제로"],
    "MG4a": ["MG4a", "MG4A", "메가드림", "메가 드림", "MEGA 드림", "드림 ex", "MEGA 드림 ex"],
    "SV2a": ["151", "포켓몬151", "포켓몬 카드151", "포켓몬카드151", "카드151"],
    "S10a": ["포켓몬 GO", "포켓몬GO", "포켓몬go", "포켓몬고", "Pokemon GO", "Pokémon GO", "pokemongo"],
}

# DB 세트명과 번개장터·박스 표기가 다른 경우 (공식/시장 표기)
BOX_MARKETPLACE_ALIASES: dict[str, list[str]] = {
    "SV2P": ["스노우해저드", "스노우 해저드"],
    "SV3": ["흑염의 카리스마"],
    "SV3a": ["레이징 서프"],
    "SV4M": ["미래의 일격"],
    "SV4": ["와일드 포스"],
    "SV4x": ["사이버 저지"],
    "SV5M": ["크림슨 헤이즈"],
    "SV5a": ["나이트 원더러"],
    "SV6": ["스텔라 미라클"],
    "SV6a": ["낙원 드라고나"],
    "SV7": ["초전 브레이커"],
    "SV8": ["테라스탈 페스타", "테라스탈 페스"],
    "SV8a": ["배틀 파트너즈"],
    "MG2": ["블랙 볼트"],
    "MG2a": ["화이트 플레어"],
    "MG3": ["메가 브레이브"],
    "MG3a": ["메가 심포니아"],
    "MG4": ["인페르노 X"],
    "MG5": ["무니키스 제로", "무니키스제로"],
    "MG5a": ["닌자 스피너"],
    "MG6": ["어비스 아이"],
    "MG7": ["스톰 에메랄다", "스톰에메랄다"],
    "SV1S": ["스칼렛 ex", "스칼렛ex"],
    "SV1V": ["바이올렛 ex", "바이올렛ex"],
    "SV1a": ["트리플렛비트"],
    "SV2D": ["클레이 버스트"],
    "S6H": ["이브이히어로즈"],
    "S6G": ["칠흑의가이스트"],
    "S6L": ["백은의랜스"],
    "S11": ["로스트어비스"],
    "S12": ["패러다임트리거"],
    "S12a": ["VSTAR유니버스"],
    "SM5": ["울트라 포스"],
    "SM4+": ["울트라 문"],
    "SM4": ["울트라 썬"],
}


def aliases_for_set_code(set_code: str) -> list[str]:
    code = (set_code or "").strip()
    if not code:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for mapping in (SET_CODE_ALIASES, BOX_MARKETPLACE_ALIASES):
        for key, vals in mapping.items():
            if key.upper() != code.upper():
                continue
            for val in vals:
                v = val.strip()
                if v and v not in seen:
                    seen.add(v)
                    out.append(v)
    return out


# 구형(번개장터 매물 희박) 세트 코드 접두사 — slim 모드에서 쿼리 3개로 줄임
_LEGACY_PREFIXES = ("SM", "XY", "BW", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12")


def is_legacy_set(set_code: str) -> bool:
    """SM/XY 등 구형 팩 여부 — 번개장터 매물이 희박해 slim 쿼리 사용."""
    code = set_code.strip().upper()
    return any(code.startswith(p) for p in _LEGACY_PREFIXES)


def build_search_queries(
    set_name_kr: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    *,
    slim: bool = False,
) -> list[str]:
    """등급·세트·카드번호·한글판을 포함한 검색어 목록.

    slim=True: 구형 팩처럼 매물이 희박한 경우 핵심 쿼리 3개만 반환.
    """
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

    if not slim:
        # 신형 팩에서만 사용하는 보조 쿼리들
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


def build_promo_search_queries(
    name_kr: str,
    card_number: str = "",
    promo_source: str = "",
    set_code: str = "",
) -> list[str]:
    """프로모(P) 카드 — 세트명 없이 증정·이벤트 키워드 중심."""
    base = name_kr.strip()
    num = card_number.strip()
    queries: list[str] = [
        f"포켓몬카드 {base} 프로모 한글",
        f"포켓몬카드 {base} 프로모",
        f"포켓몬카드 {base} P 한글",
        f"포켓몬카드 {base} P",
    ]
    if promo_source:
        queries.append(f"포켓몬카드 {promo_source} {base} 프로모")
        queries.append(f"포켓몬카드 {promo_source} {base} {num}".strip())
    if num:
        queries.append(f"포켓몬카드 {base} {num} 프로모")
        queries.append(f"포켓몬카드 {num} {base} 프로모")
        queries.append(f"포켓몬카드 {num} {base}")
    if set_code.upper() == "CEL25PK":
        queries.extend([
            f"포켓몬카드 25주년 프로모 {base}",
            f"포켓몬카드 25주년 기념 프로모팩 {base}",
            f"포켓몬카드 s8aP {base}",
        ])
    promo_aliases: dict[str, list[str]] = {
        "로켓단 등장!": ["로켓단 포스터", "로켓단세인상", "로켓단 등장"],
        "_____의 피카츄": ["생일피카츄", "생일 피카츄", "피카츄 생일", "의 피카츄"],
        "R단의 썬더": ["R단 썬더", "로켓단 번개", "로켓단 썬더"],
        "마그마단의 그란돈": ["마그마단 그란돈", "마그마 그란돈"],
        "렌트라 GL LV.X": ["렌트라 GL", "렌트라 LVX", "렌트라 GL LVX"],
        "한카리아스 C LV.X": ["한카리아스 LVX", "한카리아스 C", "가브리아스 LVX"],
        "M 레쿠쟈 EX": ["M레쿠쟈", "메가레쿠쟈", "M 레쿠쟈 ex"],
        "뮤츠 EX": ["뮤츠ex", "뮤츠 ex"],
    }
    for alias in promo_aliases.get(base, []):
        queries.append(f"포켓몬카드 {alias} 프로모")
        queries.append(f"포켓몬카드 25주년 {alias}")
    if base == "잉어킹" or "잉어킹" in base:
        queries.extend([
            "포켓몬카드 잉어킹 MEGA Festa 프로모",
            "포켓몬카드 MEGA Festa 잉어킹",
            "포켓몬카드 잉어킹 040/M-P",
            "포켓몬카드 잉어킹 M-P",
        ])

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
    has_rarity_token = any(tok.upper() in t for tok in tokens)

    if r == "RR":
        for block in RARITY_BLOCK_ABOVE.get("RR", []):
            for bt in RARITY_TOKENS.get(block, [block]):
                if bt.upper() in t and not has_rarity_token:
                    return False
        return True

    if not has_rarity_token:
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


def parse_listing_quantity(title: str) -> int:
    """제목에서 동일 카드 매수 추정 (2장·3매·x3 등). 없으면 1."""
    qty = 1
    for pat in QUANTITY_PATTERNS:
        m = pat.search(title)
        if not m:
            continue
        n = int(m.group(1))
        if 2 <= n <= MAX_SINGLE_LISTING_QTY:
            qty = max(qty, n)
    return qty


def unit_price_from_listing(
    total_price: int,
    title: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    set_name_kr: str = "",
    *,
    relaxed: bool = False,
) -> int | None:
    """총액 → 1장당 가격. 다종·묶음 매물은 None."""
    if total_price < 300 or total_price > 5_000_000:
        return None
    if relaxed:
        if not _title_matches_name(title, name_kr):
            return None
        if not _title_matches_rarity(title, rarity):
            return None
        if _is_graded_listing(title) or _is_japanese_listing(title):
            return None
        if _is_bundle_listing(title, name_kr):
            return None
    elif not is_raw_kr_listing(title, name_kr, rarity, card_number, set_code, set_name_kr):
        return None

    qty = parse_listing_quantity(title)
    unit = total_price // qty
    if unit < 300 or unit > 5_000_000:
        return None
    return unit


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


def _is_buy_listing(title: str) -> bool:
    return any(k in title for k in BUY_KEYWORDS)


def _promo_listing_valid(title: str, card_number: str) -> bool:
    """M-P 등 프로모 번호 — 오매칭(30주년·빛나는 등) 제외."""
    num = (card_number or "").strip().upper()
    if "/M-P" not in num:
        return True
    t = title
    if any(w in t for w in ("30주년", "빛나는", "010/025", "s8a-P", "S8A-P", "일판", "일본", "일어")):
        return False
    if PROMO_MP_NUMBER_RE.search(num) and num.replace(" ", "") in t.replace(" ", "").upper():
        return True
    if any(k in t.upper() for k in ("MEGA", "FESTA", "페스타", "M-P", "040/M-P", "2026")):
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
    if _is_buy_listing(title):
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
    if not _promo_listing_valid(title, card_number):
        return False

    num = card_number.strip()
    if num:
        matches = CARD_NUMBER_RE.findall(title)
        promo_matches = PROMO_MP_NUMBER_RE.findall(title)
        if matches and num not in matches:
            if not promo_matches or num.upper() not in [m.upper() for m in promo_matches]:
                return False

    return True


def filter_bunjang_listings(
    items: list[dict],
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    set_name_kr: str = "",
    *,
    relaxed: bool = False,
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
        if relaxed:
            if not _title_matches_name(title, name_kr):
                continue
            if not _title_matches_rarity(title, rarity):
                continue
            if _is_graded_listing(title) or _is_japanese_listing(title):
                continue
            unit = unit_price_from_listing(
                price, title, name_kr, rarity, card_number, set_code, set_name_kr, relaxed=True,
            )
        else:
            unit = unit_price_from_listing(
                price, title, name_kr, rarity, card_number, set_code, set_name_kr,
            )
        if unit is None:
            continue
        prices.append(unit)
    return prices


def filter_prices_by_rarity_band(prices: list[int], rarity: str) -> list[int]:
    """등급별 이상치 필터 (상·하한 강제 아님 — 밴드 밖은 제외 후 없으면 원본)."""
    if not prices:
        return prices
    bands: dict[str, tuple[int, int]] = {
        "AR": (500, 15_000),
        "RR": (300, 3_500),
        "SR": (500, 80_000),
        "SAR": (3_000, 250_000),
        "MUR": (30_000, 800_000),
        "MA": (3_000, 300_000),
        "UR": (3_000, 200_000),
        "ACE": (5_000, 150_000),
        "HR": (3_000, 150_000),
        "SSR": (5_000, 150_000),
        "P": (1_000, 500_000),
    }
    lo, hi = bands.get(rarity.upper(), (300, 3_000_000))
    filtered = [p for p in prices if lo <= p <= hi]
    return filtered if filtered else prices


def calculate_trimmed_mean(prices: list[int]) -> int:
    """상·하위 10% 제외 평균 (대표 시세용)."""
    if not prices:
        return 0
    if len(prices) < 3:
        return sum(prices) // len(prices)
    sorted_prices = sorted(prices)
    trim = max(1, len(sorted_prices) // 10)
    trimmed = sorted_prices[trim:-trim] if len(sorted_prices) > trim * 2 else sorted_prices
    return sum(trimmed) // len(trimmed)


def calculate_conservative_price(prices: list[int]) -> int:
    """실거래·저가 중심 대표가 (하위 25%ile, 최소 1건)."""
    if not prices:
        return 0
    sorted_prices = sorted(prices)
    if len(sorted_prices) == 1:
        return sorted_prices[0]
    idx = max(0, (len(sorted_prices) - 1) // 4)
    return sorted_prices[idx]


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
