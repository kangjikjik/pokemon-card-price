"""등급별 시세 검색 키워드·리스팅 필터 (미등급·한글판 위주)."""
from __future__ import annotations

import re

_LATIN_MEGA = re.compile(r"メga|메ga")  # Latin/Mix ga → 한글 가


def normalize_mega_spelling(text: str) -> str:
    """メga·메ga → 메가 — DB·검색·제목매칭 공통."""
    if not text:
        return text
    return _LATIN_MEGA.sub("메가", text)


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
    # BWR에 "BW"를 넣지 않는다. 판정은 BOUNDED_RARITY_CODES (§3.1).
    "BWR": ["BWR"],
    "MA": ["MA", "메가어택"],
    "FUR": ["FUR"],
}

# 부분 문자열로 통과시키면 안 되는 등급. TRADE_CRAWL_CRITERIA.md §3.1
# BW ⊂ BWR 처럼 짧은 코드가 검색·제목에 섞여도 긴 등급으로 저장하지 않는다.
BOUNDED_RARITY_CODES = frozenset({"BWR"})

# S등급 제목에 다른 등급 코드가 있으면 이로치 매물이 아니다. S 한 글자는 없어도 된다.
_NON_S_RARITY_RE = re.compile(
    r"(?<![A-Za-z])(?:MUR|SAR|SSR|CSR|CHR|RRR|BWR|ACE|FUR|HR|SR|AR|UR|RR|TR|PR|MA)(?![A-Za-z])",
    re.IGNORECASE,
)

CARD_NUMBER_RE = re.compile(r"\b(\d{1,3}/\d{1,3})\b")

# 체결 N건 미만이면 호가 우선 (번개 표본 부족)
MIN_SOLD_FOR_AGGREGATE = 10


def normalize_card_number(num: str) -> str:
    """015/081 → 15/081 (번개 제목·DB 번호 형식 통일)."""
    n = (num or "").strip()
    if "/" not in n:
        return n
    left, right = n.split("/", 1)
    try:
        return f"{int(left)}/{right}"
    except ValueError:
        return n


def card_number_in_title(title: str, card_number: str) -> bool:
    """제목에 카드번호가 있으면 정규화 후 비교, 없으면 통과."""
    num = normalize_card_number(card_number)
    if not num:
        return True
    matches = CARD_NUMBER_RE.findall(title)
    if not matches:
        return True
    norm_matches = {normalize_card_number(m) for m in matches}
    return num in norm_matches

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

# 한국 크롤에서 제외 — 일판·북미 등 (제목에 일판 미표기 일본 고가 매물 방지)
FOREIGN_FOR_KR = [
    "일본판", "일판", "일본", "일어", "JP", "jp", "日本", "japanese", "영문판", "영판", "미판",
    "Japanese", "English", "EN ", " EN", "海外", "북미", "미국판", "북미판",
    "중판", "중국판", "중국어판", "중국어", "중국",
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

# 띠부띠부씰·인형·몬콜레·스케일월드 등 싱글 카드가 아닌 상품
GOODS_EXCLUDE_KEYWORDS = [
    "띠부실", "띠부씰", "띠부띠부", "띠부", "굿즈)",
    "인형", "몬콜레", "몬 콜레", "스케일월드",
]

# 포켓몬 이름 바로 뒤에 붙어도 같은 카드인 표기. 메탕구의 '구'는 여기 없다.
_NAME_TAIL_PREFIXES = (
    "이로치",
    "카드",
    "일판",
    "한판",
    "일본판",
    "한국판",
    "한글판",
    "일어판",
)

PROMO_MP_NUMBER_RE = re.compile(r"\d{2,3}/M-P", re.I)

# 동일 카드 N장 — 장당 환산 (제외하지 않음)
QUANTITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(\d{1,2})\s*장(?!\s*(?:세트|판|팝|식))"),
    re.compile(r"(\d{1,2})\s*매"),
    re.compile(r"(\d{1,2})\s*개"),
    # "EX 112/081"의 X를 수량 x11로 오인하지 않도록 앞에 글자가 없을 때만
    re.compile(r"(?<![A-Za-z가-힣])[xX×]\s*(\d{1,2})\b"),
    re.compile(r"(\d{1,2})\s*[xX×](?!\d)"),
]

MAX_SINGLE_LISTING_QTY = 20

SET_CODE_ALIASES: dict[str, list[str]] = {
    "MG7": ["MG7", "M6", "m6", "스톰에메랄다", "스톰 에메랄다", "스톰에메랄드", "스톰 에메랄드", "스토에메랄da", "스토 에메랄da", "에메랄da"],
    "MG6": ["MG6", "M5", "m5", "어비스아이", "어비스 아이"],
    "MG5": ["MG5", "니힐제로", "니힐 제로"],
    "MG4a": [
        "MG4a", "MG4A", "메가드림", "메가 드림", "메가드림ex",
        "메가 드림 ex", "MEGA 드림", "드림 ex", "MEGA 드림 ex",
    ],
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
    "MG7": ["스톰 에메랄다", "스톰에메랄다", "스톰에메랄드", "스톰 에메랄드", "스토에메랄da", "스토 에메랄da", "에메랄da"],
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
    "CEL": ["25주년 기념", "25주년기념", "25주년 컬렉션", "25th Anniversary"],
    "CEL30": ["30주년 기념", "30주년", "30th CELEBRATION", "30th Celebration"],
    "CEL25PK": [
        "25주년 프로모팩",
        "25주년 기념 프로모팩",
        "25주년 프로모 카드팩",
        "프로모 카드팩",
        "s8aP",
        "s8a-P",
    ],
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


COMMEMORATIVE_YEAR_IN_TITLE: dict[str, str] = {
    "CEL": "25주년",
    "CEL30": "30주년",
    "CEL25PK": "25주년",
}

def is_commemorative_card_set(set_code: str) -> bool:
    return (set_code or "").upper() in COMMEMORATIVE_YEAR_IN_TITLE


def title_has_commemorative_year(title: str, set_code: str) -> bool:
    """CEL/CEL30 — 제목에 25주년·30주년 표기가 있어야 동일 세트 카드로 인정."""
    required = COMMEMORATIVE_YEAR_IN_TITLE.get((set_code or "").upper())
    if not required:
        return True
    return required in title


def title_is_other_commemorative(title: str, set_code: str) -> bool:
    """기념 세트가 아닌 카드에 25주년·30주년 매물이 섞이면 제외."""
    if (set_code or "").upper() in COMMEMORATIVE_YEAR_IN_TITLE:
        return False
    text = title or ""
    return "30주년" in text or "25주년" in text


_FORM_TOKENS = ("VSTAR", "VMAX", "GX", "V")


def card_form_token(name_kr: str) -> str | None:
    """카드명의 VSTAR·VMAX·GX·V. ex는 생략 가능하므로 여기서 다루지 않는다."""
    compact = re.sub(r"\s+", "", normalize_mega_spelling(name_kr or "")).upper()
    for token in _FORM_TOKENS:
        if compact.endswith(token):
            return token
    return None


def title_has_card_form(title: str, name_kr: str) -> bool:
    """님피아 V는 제목에 V가 있어야 한다. VMAX·VSTAR·GX는 서로 다른 카드다."""
    token = card_form_token(name_kr)
    if not token:
        return True
    text = title or ""
    if token == "V":
        if re.search(r"VMAX|VSTAR", text, re.I):
            return False
        return re.search(r"(?<![A-Za-z])V(?!MAX|STAR|[A-Za-z])", text, re.I) is not None
    if token == "GX":
        return re.search(r"(?<![A-Za-z])GX(?![A-Za-z])", text, re.I) is not None
    return re.search(rf"(?<![A-Za-z]){token}(?![A-Za-z])", text, re.I) is not None


def title_matches_set_discriminator(
    title: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
) -> bool:
    """같은 이름·등급이 여러 팩에 있을 때 팩 또는 카드번호로 가른다."""
    code = (set_code or "").upper()
    r = (rarity or "").upper()
    text = title or ""
    compact = re.sub(r"\s+", "", text)
    if r == "S":
        return "이로치" in text and not title_has_non_s_rarity(text)
    if code == "SV4" and "팬텀" in (name_kr or "") and r == "RR":
        return "와일드포스" in compact or "와일드 포스" in text
    if "님피아" in (name_kr or "") and card_form_token(name_kr) == "V" and r == "RR":
        lowered = text.lower()
        if "드림기프트" in text or "vmax" in lowered:
            return False
        if code == "S6H" and ("s8b" in lowered or "073/184" in text):
            return False
        if code == "S8B" and ("040/069" in text or "s6h" in lowered):
            return False
    if "무쇠무인" in (name_kr or "") and r == "SAR" and code in ("SV4M", "SV8"):
        has_future = (
            "미래의 일섬" in text
            or "미래일섬" in compact
            or "089/066" in text
            or "89/066" in text
        )
        has_tera = "테라스탈" in text or "테라스텔" in text or "213/187" in text
        if code == "SV4M":
            return has_future and not has_tera
        return has_tera and not has_future
    return True


def title_has_cc_reprint(title: str, rarity: str) -> bool:
    """CC(복각) — 제목에 복각 표기 필수 (구세트·오매칭 제외)."""
    if (rarity or "").upper() != "CC":
        return True
    return "복각" in title


PIKACHU_PKR_NAME_RE = re.compile(r"^(\d+)번\s*피카츄$", re.I)


def pikachu_pkr_index(name_kr: str) -> int | None:
    m = PIKACHU_PKR_NAME_RE.match((name_kr or "").strip())
    return int(m.group(1)) if m else None


def match_pikachu_pkr_name_in_title(title: str, name_kr: str) -> bool:
    """30주년 PKR — 번개 표기 `피카츄 N번` / `N번 피카츄` 모두 인정."""
    idx = pikachu_pkr_index(name_kr)
    if idx is None:
        return False
    compact = re.sub(r"\s+", "", title)
    patterns = (
        f"{idx}번피카츄",
        f"피카츄{idx}번",
        f"{idx}번 피카츄",
        f"피카츄 {idx}번",
    )
    return any(p.replace(" ", "") in compact for p in patterns)


def is_cel30_cc(set_code: str, rarity: str) -> bool:
    """30주년 Classic Collection(CC) — 번개 검색·제목에 등급 표기가 거의 없음."""
    return (set_code or "").upper() == "CEL30" and (rarity or "").upper() == "CC"


def commemorative_card_search_queries(
    prefix: str,
    name_kr: str,
    rarity: str,
    set_name_kr: str = "",
    set_code: str = "",
) -> list[str]:
    """기념 세트(COL/CEL30) — 25주년·30주년 접두 검색어 (CC는 복각 포함)."""
    r = (rarity or "").upper()
    base = normalize_mega_spelling(name_kr.strip())
    queries: list[str] = []
    idx = pikachu_pkr_index(base)
    if idx is not None:
        queries.extend([
            f"{prefix} 피카츄 {idx}번",
            f"포켓몬카드 {prefix} 피카츄 {idx}번",
            f"{prefix} {idx}번 피카츄",
            f"포켓몬카드 {prefix} {idx}번 피카츄",
        ])
    elif is_cel30_cc(set_code, r) and base:
        queries.extend([
            f"{prefix} 복각 {base}",
            f"포켓몬카드 {prefix} 복각 {base}",
        ])
    elif base and r:
        compact = re.sub(r"\s+", "", base)
        queries.extend([
            f"포켓몬카드 {prefix} {base} {r}",
            f"{prefix} {base} {r}",
            f"포켓몬카드 {prefix} {base}{r}",
            f"{prefix} {base}{r}",
            f"포켓몬카드 {prefix} {compact}{r}",
        ])
        if set_name_kr:
            queries.append(f"포켓몬카드 {set_name_kr} {base} {r}")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def build_search_queries(
    set_name_kr: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    *,
    slim: bool = False,
) -> list[str]:
    """번개 검색어 — **카드명 + 등급** 우선 (M5·MG6·팩번호 검색 금지).

    slim=True: 구형 팩처럼 매물이 희박한 경우 핵심 쿼리만 반환.
    """
    base = normalize_mega_spelling(name_kr.strip())
    r = rarity.upper()
    compact = re.sub(r"\s+", "", base)
    # Collectory 공식명(그로우 풀에너지) ↔ 번개 검색(그로우 풀 에너지)
    name_variants = [base]
    spaced_energy = re.sub(r"(풀|불꽃|물)(에너지)", r"\1 \2", base)
    if spaced_energy != base:
        name_variants.append(spaced_energy)

    commemorative_prefix = COMMEMORATIVE_YEAR_IN_TITLE.get((set_code or "").upper())
    queries: list[str] = []
    is_energy = bool(re.search(r"(풀|불꽃|물)\s*에너지", base))
    code = (set_code or "").upper()

    def finish(found: list[str]) -> list[str]:
        from lib.art_split import extra_split_art_queries  # noqa: PLC0415

        merged = list(found)
        merged.extend(
            extra_split_art_queries(set_name_kr, base, r, card_number, set_code)
        )
        return _dedupe_queries(merged)

    if r == "S" and base:
        return finish(shiny_s_search_queries(base))

    if code == "SV4M" and "무쇠무인" in base and r == "SAR":
        return finish([
            "미래의 일섬 무쇠무인 ex sar",
            "미래의 일섬 무쇠무인ex sar",
            "포켓몬카드 미래의 일섬 무쇠무인 ex sar",
        ])

    if code == "SV8" and "무쇠무인" in base and r == "SAR":
        return finish([
            "테라스탈 페스타 무쇠무인 ex sar",
            "테라스탈페스타 무쇠무인 ex sar",
            "테라스텔 페스타 무쇠무인 ex sar",
        ])

    if code == "SV4" and "팬텀" in base and r == "RR":
        queries.extend([
            "와일드 포스 팬텀 ex rr",
            "와일드포스 팬텀 ex rr",
            "포켓몬카드 와일드 포스 팬텀 ex rr",
        ])

    if commemorative_prefix:
        for nm in name_variants:
            queries.extend(
                commemorative_card_search_queries(
                    commemorative_prefix, nm, r, set_name_kr, set_code
                )
            )
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            q = re.sub(r"\s+", " ", q).strip()
            if q and q not in seen:
                seen.add(q)
                out.append(q)
        return finish(out)

    # 1순위: 사람들이 실제로 치는 형태
    for nm in name_variants:
        c = re.sub(r"\s+", "", nm)
        if nm and r:
            queries.append(f"{nm} {r}")
            queries.append(f"{nm}{r}")
        if c and c != nm and r:
            queries.append(f"{c} {r}")
            queries.append(f"{c}{r}")
        # 에너지 SR — 번개 검색에 SR 없이 올리는 경우 많음
        if is_energy and nm:
            queries.append(nm)
            if c != nm:
                queries.append(c)
    if compact and compact != base and r:
        queries.append(f"{compact} {r}")
        queries.append(f"{compact}{r}")

    if not slim:
        for nm in name_variants:
            if set_name_kr and nm and r:
                queries.append(f"포켓몬카드 {set_name_kr} {nm} {r} 한글")
                queries.append(f"포켓몬카드 {set_name_kr} {nm} {r}")
                queries.append(f"{set_name_kr} {nm} {r}")
            if nm and r:
                queries.append(f"포켓몬카드 {nm} {r}")
        short_name = base
        for prefix in ("메가", "Mega ", "mega "):
            if short_name.startswith(prefix):
                short_name = short_name[len(prefix) :].strip()
                break
        if short_name and short_name != base and r:
            queries.append(f"{short_name} {r}")
            queries.append(f"포켓몬카드 {short_name} {r}")
        if compact.startswith("메가") and len(compact) > len("메가"):
            rest = compact[len("메가") :].strip()
            if rest and r:
                queries.append(f"메가 {rest} {r}")
                queries.append(f"메가{rest}{r}")

    return finish(queries)


def _dedupe_queries(queries: list[str]) -> list[str]:
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
    """프로모(P) KR 검색어 (TRADE_CRAWL_CRITERIA.md §17.2)."""
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
            f"25주년 {base} 프로모",
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


def build_promo_jp_search_queries(
    name_kr: str,
    card_number: str = "",
    promo_source: str = "",
    set_code: str = "",
) -> list[str]:
    """프로모(P) JP 검색어 — KR 검색어 + 일판, 한국 한정은 [] (§17.3)."""
    from lib.promo_exclusive import is_kr_exclusive_promo  # noqa: PLC0415

    if is_kr_exclusive_promo(set_code, card_number):
        return []  # §16.3: JP 검색 자체를 하지 않음

    base = name_kr.strip()
    queries: list[str] = []
    for q in build_promo_search_queries(name_kr, card_number, promo_source, set_code):
        if "일판" in q or "일본" in q:
            queries.append(q)
            continue
        queries.append(f"{q} 일판")
        if "한글" in q:
            queries.append(q.replace("한글", "일판"))
    if set_code.upper() == "CEL25PK":
        queries.extend([
            f"25주년 {base} 일판",
            f"포켓몬카드 25주년 {base} 일판",
            f"포켓몬카드 25주년 프로모 {base} 일판",
            f"25주년 프로모 {base} 일판",
        ])
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def title_has_bounded_rarity(title: str, code: str) -> bool:
    """영문 등급 코드. 뒤에 영문이 더 붙으면 다른 등급이다.

    번개 검색어 ``이름BWR`` 은 ``이름 BW`` 매물까지 돌려준다.
    ``BW`` 는 ``BWR`` 이 아니고, ``BWRR`` 도 ``BWR`` 이 아니다.
    카드명에 붙어 있는 ``제크로무exBWR`` 은 인정한다.
    """
    if not code:
        return False
    return re.search(rf"{re.escape(code)}(?![A-Za-z])", title or "", re.IGNORECASE) is not None


def title_has_non_s_rarity(title: str) -> bool:
    """S가 아닌 영문 등급 코드. S 한 글자·S급은 여기서 다루지 않는다."""
    return _NON_S_RARITY_RE.search(title or "") is not None


def shiny_s_search_queries(name_kr: str) -> list[str]:
    """S등급 검색어. 등급 코드 없이 포켓몬 이름 + 이로치."""
    base = normalize_mega_spelling((name_kr or "").strip())
    if not base:
        return []
    compact = re.sub(r"\s+", "", base)
    queries = [
        f"{base} 이로치",
        f"포켓몬카드 {base} 이로치",
    ]
    if compact != base:
        queries.append(f"{compact} 이로치")
    return _dedupe_queries(queries)


def _title_matches_rarity(title: str, rarity: str, set_code: str = "") -> bool:
    if is_cel30_cc(set_code, rarity):
        return True
    t = title.upper()
    r = rarity.upper()
    if r == "S":
        return not title_has_non_s_rarity(title)
    if r in BOUNDED_RARITY_CODES:
        return title_has_bounded_rarity(title, r)
    tokens = RARITY_TOKENS.get(r, [r])
    has_rarity_token = any(tok.upper() in t for tok in tokens)

    if r == "RR":
        for block in RARITY_BLOCK_ABOVE.get("RR", []):
            for bt in RARITY_TOKENS.get(block, [block]):
                if bt.upper() in t:
                    return False
        return has_rarity_token or " RR" in f" {title.upper()} " or title.upper().startswith("RR ")

    if not has_rarity_token:
        if r in ("SR", "SAR", "AR", "MUR", "UR", "ACE"):
            return False
        return True
    for block in RARITY_BLOCK_ABOVE.get(r, []):
        for bt in RARITY_TOKENS.get(block, [block]):
            if bt.upper() in t:
                return False
    return True


def _compact_match_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _is_hangul_char(ch: str) -> bool:
    return len(ch) == 1 and "가" <= ch <= "힣"


def _hangul_tail_allowed(rest: str) -> bool:
    """이름 직후 한글은 이로치·카드·일판만 허용. 메탕구처럼 이어지면 다른 이름."""
    tails = sorted(_NAME_TAIL_PREFIXES, key=len, reverse=True)
    s = rest
    while s and _is_hangul_char(s[0]):
        matched = False
        for tail in tails:
            if s.startswith(tail):
                s = s[len(tail):]
                matched = True
                break
        if not matched:
            return False
    return True


def name_matches_spaced_title(title: str, name: str) -> bool:
    """제목에 있는 띄어쓰기는 유지한다. 이름 안의 띄어쓰기만 무시한다."""
    raw = re.sub(r"\s+", "", (name or "")).lower()
    if len(raw) < 2 or not title:
        return False
    title_l = title.lower()
    pattern = r"\s*".join(re.escape(ch) for ch in raw)
    for match in re.finditer(pattern, title_l):
        start = match.start()
        if start > 0 and _is_hangul_char(title_l[start - 1]):
            continue
        if _hangul_tail_allowed(title_l[match.end() :].lstrip()):
            return True
    return False


def name_token_in_text(text: str, name: str) -> bool:
    """이름이 더 긴 한글 이름에 끼어 있으면 불일치. 메탕은 메탕구가 아니고, 코일은 레어코일이 아니다."""
    name = (name or "").strip()
    if len(name) < 2 or not text:
        return False
    start = 0
    while True:
        i = text.find(name, start)
        if i < 0:
            return False
        if i > 0 and _is_hangul_char(text[i - 1]):
            start = i + 1
            continue
        if _hangul_tail_allowed(text[i + len(name):]):
            return True
        start = i + 1


def _title_matches_name(title: str, name_kr: str) -> bool:
    name = normalize_mega_spelling(name_kr.strip())
    if not name:
        return True
    if match_pikachu_pkr_name_in_title(title, name):
        return True
    core = name
    for suf in [" 프로모", " ex", " EX", " VSTAR", " VMAX", " V", " GX"]:
        if core.endswith(suf):
            core = core[: -len(suf)].strip()
            break
    if len(core) >= 2 and name_matches_spaced_title(title, core):
        return True
    if name != core and name_matches_spaced_title(title, name):
        return True
    if core.startswith("메가") and len(core) > 2:
        short = core[len("메가") :].strip()
        if len(short) >= 2 and name_matches_spaced_title(title, short):
            return True
    return False


def _is_japanese_listing(title: str) -> bool:
    t = title
    if any(k in t for k in KR_KEYWORDS):
        return False
    return any(k in t for k in JP_KEYWORDS + FOREIGN_FOR_KR)


def _is_multi_card_sale(title: str, name_kr: str) -> bool:
    """다른 카드와 묶음·일괄 판매 (단품 아님)."""
    if any(k in title for k in ("일괄", "묶음", "세트", "SET", "set", "통판", "종세트")):
        return True
    nums = {normalize_card_number(n) for n in CARD_NUMBER_RE.findall(title)}
    if len(nums) >= 2:
        return True
    if re.search(r"[,+&]", title):
        parts = re.split(r"[,+&]", title)
        graded_parts = 0
        for p in parts:
            pu = f" {p.upper()} "
            if any(g in pu for g in (" SR ", " SAR ", " RR ", " AR ", " EX ", " MUR ", "BRG", "PSA")):
                graded_parts += 1
        if graded_parts >= 2:
            return True
        other_named = sum(
            1 for p in parts
            if len(p.strip()) >= 3 and name_kr not in p and not _title_matches_name(p, name_kr)
        )
        if graded_parts >= 1 and other_named >= 1:
            return True
    if "+" in title:
        left, _, right = title.partition("+")
        if (
            len(left.strip()) >= 3
            and len(right.strip()) >= 3
            and not _title_matches_name(right, name_kr)
        ):
            return True
    if "/" in title and not CARD_NUMBER_RE.search(title):
        parts = [p.strip() for p in title.split("/") if len(p.strip()) >= 2]
        if len(parts) >= 2:
            name_hits = sum(1 for p in parts if _title_matches_name(p, name_kr))
            other_named = sum(
                1 for p in parts
                if len(p.strip()) >= 2 and not _title_matches_name(p, name_kr)
            )
            if name_hits >= 1 and other_named >= 1:
                return True
    return False


def filter_median_outliers(
    prices: list[int],
    *,
    max_ratio: float = 1.5,
    min_ratio: float = 0.65,
    min_samples: int = 4,
) -> list[int]:
    """중앙값 대비 비정상 고가·저가 제거 (일판 오매칭·묶음 잔여)."""
    clean = [p for p in prices if p > 0]
    if len(clean) < min_samples:
        return clean
    med = sorted(clean)[len(clean) // 2]
    if med <= 0:
        return clean
    lo = max(int(med * min_ratio), 300)
    hi = int(med * max_ratio)
    return [p for p in clean if lo <= p <= hi]


def _is_graded_listing(title: str) -> bool:
    t = title.upper()
    return any(k.upper() in t for k in GRADED_KEYWORDS)


_SLAB_IN_TEXT_RE = re.compile(
    r"(PSA|BGS|CGC|SGC|BRG|ARS|PCG|HGA|KSA|GRAAD|GEM)\s*\d"
    r"|슬랩|그레이딩|채점|실물감정"
    r"|등급\s*\d"
    r"|\d+(?:\.\d+)?\s*점",
    re.I,
)


def text_has_slab_grade(text: str) -> bool:
    """상세 설명의 감정 점수. 제목의 S급·A급이나 'AR 등급' 문장은 해당하지 않는다."""
    if not text:
        return False
    return _SLAB_IN_TEXT_RE.search(text) is not None


def parse_listing_quantity(title: str) -> int:
    """제목에서 동일 카드 매수 추정 (2장·3매·x3 등). 없으면 1."""
    scrubbed = CARD_NUMBER_RE.sub(" ", title)
    qty = 1
    for pat in QUANTITY_PATTERNS:
        m = pat.search(scrubbed)
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
    # 콤마/플러스로 여러 카드명 나열 (단품 아님) — 015/081 슬래시는 제외
    scrubbed = CARD_NUMBER_RE.sub(" ", title)
    if re.search(r"[,+·/]", scrubbed):
        parts = re.split(r"[,+·/]", scrubbed)
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


def _is_goods_listing(title: str) -> bool:
    return any(k in title for k in GOODS_EXCLUDE_KEYWORDS)


def promo_mp_kr_listing_valid(title: str, card_number: str) -> bool:
    """M-P 프로모 KR 제목 검증 (TRADE_CRAWL_CRITERIA.md §16.3, §17.4)."""
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
    if _is_goods_listing(title):
        return False
    if _is_graded_listing(title):
        return False
    if title_is_other_commemorative(title, set_code):
        return False
    if not title_has_card_form(title, name_kr):
        return False
    if not title_matches_set_discriminator(title, name_kr, rarity, card_number, set_code):
        return False
    if _is_japanese_listing(title):
        return False
    if _is_bundle_listing(title, name_kr):
        return False
    if _is_multi_card_sale(title, name_kr):
        return False
    if not title_has_commemorative_year(title, set_code):
        return False
    if not title_has_cc_reprint(title, rarity):
        return False
    if not _title_matches_name(title, name_kr):
        return False
    if not _title_matches_rarity(title, rarity, set_code):
        from lib.trainer_item_cards import skip_card_number_in_title  # noqa: PLC0415

        # MEGA 트레이너·에너지 SR — 번개 제목에 SR 미표기인 경우가 많음
        if (
            set_code.upper().startswith("MG")
            and (rarity or "").upper() == "SR"
            and skip_card_number_in_title(set_code, card_number, "")
            and _title_matches_name(title, name_kr)
        ):
            tu = title.upper()
            if any(tok in tu for tok in ("SAR", " AR ", " ACE ", " MUR ", " UR ")):
                return False
        else:
            return False
    if not promo_mp_kr_listing_valid(title, card_number):
        return False

    from lib.trainer_item_cards import skip_card_number_in_title  # noqa: PLC0415

    num = card_number.strip()
    if num and not skip_card_number_in_title(set_code, card_number):
        if not card_number_in_title(title, num):
            promo_matches = PROMO_MP_NUMBER_RE.findall(title)
            if not promo_matches or num.upper() not in [m.upper() for m in promo_matches]:
                return False

    from lib.art_split import title_matches_split_art  # noqa: PLC0415

    if not title_matches_split_art(
        title, name_kr, rarity, card_number, set_code, set_name_kr
    ):
        return False

    return True


# 하위 호환
_promo_listing_valid = promo_mp_kr_listing_valid


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
            if not _title_matches_rarity(title, rarity, set_code):
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


def filter_prices_pipeline(prices: list[int], rarity: str) -> list[int]:
    """등급 밴드 → 중앙값 이상치 순 필터."""
    banded = filter_prices_by_rarity_band(prices, rarity)
    return filter_median_outliers(banded)


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
        "CC": (5_000, 500_000),
        "PKR": (500, 50_000),
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
