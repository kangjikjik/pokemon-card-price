"""한국판 미개봉 박스 시세 — 번개장터 검색·필터."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from lib.box_image_verify import BoxImageVerifier
from lib.price_search import (
    BUY_KEYWORDS,
    CARD_NUMBER_RE,
    FOREIGN_FOR_KR,
    JP_KEYWORDS,
    KR_KEYWORDS,
    aliases_for_set_code,
    calculate_median_price,
    filter_median_outliers,
)

BOX_MARKERS = ["박스", "BOX", "box", "Box", "고대박스"]
SEALED_MARKERS = ["미개봉", "sealed", "Sealed"]
OPENED_KEYWORDS = ["개봉", "개봉품", "사용감", "뜯은", "뜯음"]
SINGLE_KEYWORDS = ["싱글", "단품", "1장", "한장", "카드만", "카드 1"]
PACK_MARKERS = ["고대팩", "부스터팩", "부스터", "booster", "Booster", "パック", "팩"]
MULTI_PACK_RE = re.compile(r"(?:\d+\s*팩|팩\s*\d+|단팩|1팩|한\s*팩)", re.I)
RARITY_MARKERS = [
    "SAR", "SR ", " SR", " AR ", " AR", "MUR", "RR ", " RR", "UR ", " ACE",
    "CSR", "CHR", "PR ", " PR", "SSR", "HR ", " HR",
    "BRG", "BGS", "CGC", "PSA",
]
BUNDLE_BOX_KEYWORDS = ["일괄", "묶음", "통판", "대량", "2종", "3종", "4종", "5종", "6종", "7종", "8종"]
MULTI_SET_BOX_RE = re.compile(r"(\d{1,2})\s*(?:박스|box|BOX)", re.I)

# 번개장터 status: 0=판매중, 1=예약중, 3=판매완료
BUNJANG_STATUS_SOLD = frozenset({"3", 3})
BUNJANG_STATUS_SELLING = frozenset({"0", 0})

# 거래완료가 이 기간보다 오래되면 판매중 호가로 전환
SOLD_MAX_AGE_DAYS = 90


@dataclass(frozen=True)
class VerifiedBoxQuote:
    price: int
    updated_at: int
    pid: str


def _box_search_name_candidates(set_name_kr: str, set_code: str) -> list[str]:
    """번개장터 검색·제목 매칭용 세트명 후보 (한글 시장 표기 우선)."""
    name = set_name_kr.strip()
    short = re.sub(r"^포켓몬\s+", "", name, flags=re.I).strip()
    cands: list[str] = []
    for raw in (short, name):
        if not raw:
            continue
        cands.append(raw)
        nospace = raw.replace(" ", "")
        if nospace != raw:
            cands.append(nospace)
    for alias in aliases_for_set_code(set_code):
        if re.fullmatch(r"[A-Za-z]{1,4}\d{1,3}[A-Za-z]?", alias.strip()):
            continue
        cands.append(alias)
        nospace = alias.replace(" ", "")
        if nospace != alias:
            cands.append(nospace)
    if set_code.upper() == "SV2A":
        cands.extend(["포켓몬카드 151", "포켓몬 카드 151"])
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def build_box_search_queries(set_name_kr: str, set_code: str) -> list[str]:
    queries: list[str] = []
    for n in _box_search_name_candidates(set_name_kr, set_code):
        queries.extend([
            f"{n} 박스",
            f"{n} 박스 미개봉",
            f"포켓몬카드 {n} 박스",
            f"포켓몬카드 {n} 박스 미개봉",
            f"포켓몬 {n} 박스",
            f"포켓몬카드 {n} 고대박스",
            f"포켓몬카드 {n} 한글판 박스",
        ])
        if set_code.upper() == "SV2A":
            queries.extend([
                f"{n} 미개봉",
                f"{n} 확장팩",
                f"{n} 강화 확장팩",
            ])
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text)
    t = unicodedata.normalize(
        "NFC", "".join(c for c in t if not unicodedata.combining(c))
    )
    t = re.sub(r"\s+", "", t.lower())
    # 번개 표기: 에메랄드 / 스토에메랄다 → 공식 스톰에메랄da
    t = t.replace("에메랄드", "에메랄da").replace("스토에메랄da", "스톰에메랄da")
    return t


def _set_name_variants(set_name_kr: str, set_code: str) -> list[str]:
    """제목 매칭·검색용 세트명 변형 (공백·ex 접미사)."""
    name = set_name_kr.strip()
    base = re.sub(r"\s*ex\s*$", "", name, flags=re.I).strip()
    variants = [name, base, name.replace(" ", ""), base.replace(" ", "")]
    for alias in aliases_for_set_code(set_code):
        variants.extend([alias, alias.replace(" ", "")])
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        n = _norm(v)
        if n and n not in seen:
            seen.add(n)
            out.append(v)
    return out


def _matches_set_token(t: str, variant: str) -> bool:
    v = _norm(variant)
    if not v:
        return False
    if v.isdigit():
        # 151 세트명 — 카드번호 151/165 와 구분
        # 세트명은 "포켓몬카드 151"로 검색·판별한다.
        if v == "151" and "포켓몬카드151" not in t:
            return False
        # BC151KR 같은 상품 코드·휴대폰 모델명에 포함된 숫자는 세트명으로 보지 않는다.
        return bool(re.search(rf"(?<![0-9A-Za-z]){re.escape(v)}(?![0-9A-Za-z/])", t))
    return v in t


def _title_matches_set(title: str, set_name_kr: str, set_code: str) -> bool:
    t = _norm(title)
    if set_code.upper() == "SV2A" and "포켓몬카드151" not in t:
        return False
    if set_code:
        code = _norm(set_code)
        if code and re.search(rf"(?<![a-z0-9]){re.escape(code)}(?![a-z0-9])", t):
            return True
    for variant in _set_name_variants(set_name_kr, set_code):
        if _matches_set_token(t, variant):
            return True
    return False


def _is_japanese_box(title: str) -> bool:
    if any(k in title for k in KR_KEYWORDS):
        return False
    return any(k in title for k in JP_KEYWORDS)


def _is_buy_listing(title: str) -> bool:
    return any(k in title for k in BUY_KEYWORDS)


def _has_box_marker(title: str) -> bool:
    return any(k in title for k in BOX_MARKERS)


def _price_suggests_box(
    unit_price: int,
    msrp_box_kr: int,
    msrp_pack_kr: int = 0,
) -> bool:
    """제목에 '고대팩'만 있어도 가격이 박스대면 박스로 본다 (판매자 표기 오류)."""
    if unit_price <= 0 or msrp_box_kr <= 0:
        return False
    pack_floor = int(max(msrp_pack_kr, 500) * 25) if msrp_pack_kr else 0
    box_floor = max(int(msrp_box_kr * 1.2), pack_floor)
    return unit_price >= box_floor


def _is_mislabeled_sealed_box(
    title: str,
    unit_price: int,
    msrp_box_kr: int,
    msrp_pack_kr: int = 0,
) -> bool:
    if not any(k in title for k in SEALED_MARKERS):
        return False
    if _has_box_marker(title):
        return False
    if not any(k in title for k in ("고대팩", "확장팩", "부스터팩", "부스터", "booster", "Booster", "パック")):
        return False
    return _price_suggests_box(unit_price, msrp_box_kr, msrp_pack_kr)


def _looks_like_pack_listing(
    title: str,
    unit_price: int = 0,
    msrp_box_kr: int = 0,
    msrp_pack_kr: int = 0,
) -> bool:
    if _has_box_marker(title):
        return False
    if unit_price and _is_mislabeled_sealed_box(title, unit_price, msrp_box_kr, msrp_pack_kr):
        return False
    if any(k in title for k in ("고대팩", "부스터팩", "부스터", "booster", "Booster", "パック")):
        return True
    if MULTI_PACK_RE.search(title):
        return True
    if "팩" in title:
        remainder = title.replace("확장팩", "")
        if "팩" in remainder:
            return True
    return False


def _looks_like_single_card(
    title: str,
    unit_price: int = 0,
    msrp_box_kr: int = 0,
    msrp_pack_kr: int = 0,
) -> bool:
    if _has_box_marker(title):
        return False
    if _looks_like_pack_listing(title, unit_price, msrp_box_kr, msrp_pack_kr):
        return True
    if CARD_NUMBER_RE.search(title):
        return True
    if any(k in title for k in SINGLE_KEYWORDS if k != "카드 1") or re.search(
        r"카드\s+1(?!\d)", title
    ):
        return True
    upper = title.upper()
    if any(m in upper for m in RARITY_MARKERS) and not _has_box_marker(title):
        return True
    return False


def _is_box_listing(
    title: str,
    unit_price: int = 0,
    msrp_box_kr: int = 0,
    msrp_pack_kr: int = 0,
) -> bool:
    if "박스폰" in title:
        return False
    if _has_box_marker(title):
        return True
    if "확장팩" in title and "팩" not in title.replace("확장팩", ""):
        return True
    if unit_price and _is_mislabeled_sealed_box(title, unit_price, msrp_box_kr, msrp_pack_kr):
        return True
    if unit_price and _price_suggests_box(unit_price, msrp_box_kr, msrp_pack_kr):
        return True
    return False


def _is_opened_box(title: str) -> bool:
    if "미개봉" in title:
        return False
    return any(k in title for k in OPENED_KEYWORDS)


def _is_bundle_box_listing(title: str, set_name_kr: str, set_code: str) -> bool:
    if any(k in title for k in BUNDLE_BOX_KEYWORDS):
        return True
    t = _norm(title)
    my = _norm(set_name_kr)
    if not my:
        return False
    # 다른 세트명이 함께 있으면 묶음 (예: 울트라문+울트라썬 일괄)
    # 동일 세트 N박스(2박스·4박스)는 _box_unit_price로 단가 환산 — 여기서 제외하지 않음
    from kr_sets import KR_BY_CODE

    for code, meta in KR_BY_CODE.items():
        if code.upper() == set_code.upper():
            continue
        other = _norm(meta.name_kr)
        if len(other) >= 3 and other in t and other != my:
            return True
        for alias in aliases_for_set_code(code):
            if len(alias) >= 3 and _norm(alias) in t:
                return True
    return False


def _box_unit_price(total_price: int, title: str) -> int | None:
    m = MULTI_SET_BOX_RE.search(title)
    if m:
        qty = int(m.group(1))
        if 2 <= qty <= 30:
            unit = total_price // qty
            return unit if unit >= 3000 else None
    return total_price


def box_price_bounds(msrp_box_kr: int, msrp_pack_kr: int = 0) -> tuple[int, int]:
    msrp = max(msrp_box_kr, 5000)
    # 박스 시세가 발매가보다 낮은 거래·호가는 모두 제외한다.
    lo = msrp
    # 구세대 고가 박스 — 상한은 비현실적 outlier만 제외
    hi = 50_000_000
    return lo, hi


def _bunjang_item_status(item: dict) -> str:
    return str(item.get("status", "0") or "0")


def _is_bunjang_sold(item: dict) -> bool:
    return _bunjang_item_status(item) in BUNJANG_STATUS_SOLD


def _is_bunjang_listing(item: dict) -> bool:
    return _bunjang_item_status(item) in BUNJANG_STATUS_SELLING


def _bunjang_update_time(item: dict) -> int:
    try:
        return int(item.get("update_time") or item.get("updated_at") or 0)
    except (TypeError, ValueError):
        return 0


def _collect_verified_box_quotes(
    items: list[dict],
    set_name_kr: str,
    set_code: str,
    msrp_box_kr: int,
    msrp_pack_kr: int,
    is_jp: bool,
    verifier: BoxImageVerifier | None,
    *,
    allow_opened: bool = False,
) -> tuple[list[VerifiedBoxQuote], list[VerifiedBoxQuote]]:
    """제목·가격·이미지 검증 통과 매물 → (거래완료, 판매중)."""
    lo, hi = box_price_bounds(msrp_box_kr, msrp_pack_kr)
    sold: list[VerifiedBoxQuote] = []
    listings: list[VerifiedBoxQuote] = []
    base_fn = is_jp_box_listing if is_jp else is_kr_box_listing

    def listing_fn(
        title: str,
        set_name: str,
        code: str,
        msrp_box: int,
        unit: int,
        msrp_pack: int,
    ) -> bool:
        return base_fn(title, set_name, code, msrp_box, unit, msrp_pack, allow_opened=allow_opened)

    for item in items:
        title = str(item.get("name", ""))
        try:
            price = int(item.get("price", 0) or 0)
        except (TypeError, ValueError):
            continue
        unit = _box_unit_price(price, title)
        if unit is None:
            continue
        if not listing_fn(title, set_name_kr, set_code, msrp_box_kr, unit, msrp_pack_kr):
            continue
        if unit < lo or unit > hi:
            continue
        if verifier is not None and not verifier.matches(item):
            continue

        pid = str(item.get("pid", "") or "")
        quote = VerifiedBoxQuote(price=unit, updated_at=_bunjang_update_time(item), pid=pid)
        if _is_bunjang_sold(item):
            if quote.updated_at > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(days=SOLD_MAX_AGE_DAYS)
                occurred = datetime.fromtimestamp(quote.updated_at, tz=timezone.utc)
                if occurred < cutoff:
                    continue
            sold.append(quote)
        elif _is_bunjang_listing(item):
            listings.append(quote)
    return sold, listings


def filter_bunjang_kr_box_quotes(
    items: list[dict],
    set_name_kr: str,
    set_code: str,
    msrp_box_kr: int,
    msrp_pack_kr: int = 0,
    verifier: BoxImageVerifier | None = None,
    *,
    allow_opened: bool = False,
) -> tuple[list[VerifiedBoxQuote], list[VerifiedBoxQuote]]:
    return _collect_verified_box_quotes(
        items, set_name_kr, set_code, msrp_box_kr, msrp_pack_kr, False, verifier,
        allow_opened=allow_opened,
    )


def filter_bunjang_jp_box_quotes(
    items: list[dict],
    set_name_kr: str,
    set_code: str,
    msrp_box_krw: int,
    msrp_pack_krw: int = 0,
    verifier: BoxImageVerifier | None = None,
    *,
    allow_opened: bool = False,
) -> tuple[list[VerifiedBoxQuote], list[VerifiedBoxQuote]]:
    return _collect_verified_box_quotes(
        items, set_name_kr, set_code, msrp_box_krw, msrp_pack_krw, True, verifier,
        allow_opened=allow_opened,
    )


def is_kr_box_listing(
    title: str,
    set_name_kr: str,
    set_code: str,
    msrp_box_kr: int,
    unit_price: int = 0,
    msrp_pack_kr: int = 0,
    *,
    allow_opened: bool = False,
) -> bool:
    if not title.strip():
        return False
    if _is_buy_listing(title):
        return False
    if _is_japanese_box(title):
        return False
    if any(k in title for k in FOREIGN_FOR_KR):
        return False
    if not _title_matches_set(title, set_name_kr, set_code):
        return False
    if not _is_box_listing(title, unit_price, msrp_box_kr, msrp_pack_kr):
        return False
    if _looks_like_single_card(title, unit_price, msrp_box_kr, msrp_pack_kr):
        return False
    if not allow_opened and _is_opened_box(title):
        return False
    if _is_bundle_box_listing(title, set_name_kr, set_code):
        return False
    return True


def filter_bunjang_box_listings(
    items: list[dict],
    set_name_kr: str,
    set_code: str,
    msrp_box_kr: int,
    msrp_pack_kr: int = 0,
) -> list[int]:
    """판매중 호가 가격만 (레거시 — 크림 등)."""
    _, listings = filter_bunjang_kr_box_quotes(
        items, set_name_kr, set_code, msrp_box_kr, msrp_pack_kr, verifier=None
    )
    return [q.price for q in listings]


def resolve_box_price(prices: list[int]) -> tuple[int, int]:
    """(average, count)."""
    if not prices:
        return 0, 0
    return round(sum(prices) / len(prices)), len(prices)


def _resolve_tier_prices(prices: list[int], tier: str) -> tuple[int, int, str]:
    uniq = sorted({p for p in prices if p > 0})
    if not uniq:
        return 0, 0, ""
    return round(sum(uniq) / len(uniq)), len(uniq), tier


def _jp_box_by_price(
    title: str,
    unit_price: int,
    msrp_box_krw: int,
    msrp_pack_krw: int,
) -> bool:
    """제목에 '박스' 없어도 일본판 표기 + 박스 가격대면 인정."""
    return (
        unit_price > 0
        and _is_japanese_box(title)
        and _price_suggests_box(unit_price, msrp_box_krw, msrp_pack_krw)
    )


def resolve_bunjang_box_price(
    sold_quotes: list[VerifiedBoxQuote],
    listing_quotes: list[VerifiedBoxQuote] | None = None,
    *,
    listing_prices: list[int] | None = None,
    max_sold_age_days: int = SOLD_MAX_AGE_DAYS,
) -> tuple[int, int, str]:
    """최근 거래완료와 판매중 호가를 함께 평균한다."""
    if listing_quotes is None:
        listing_quotes = [
            VerifiedBoxQuote(price=p, updated_at=0, pid="")
            for p in (listing_prices or [])
        ]

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_sold_age_days)
    recent_sold: list[int] = []
    for q in sold_quotes:
        if q.price <= 0:
            continue
        if q.updated_at <= 0:
            recent_sold.append(q.price)
            continue
        ts = datetime.fromtimestamp(q.updated_at, tz=timezone.utc)
        if ts >= cutoff:
            recent_sold.append(q.price)

    listing_vals = [q.price for q in listing_quotes if q.price > 0]
    filtered_values = filter_median_outliers(recent_sold + listing_vals)
    remaining: dict[int, int] = {}
    for price in filtered_values:
        remaining[price] = remaining.get(price, 0) + 1
    recent_sold_values = recent_sold
    recent_sold = []
    for price in recent_sold_values:
        if remaining.get(price, 0) > 0:
            recent_sold.append(price)
            remaining[price] -= 1
    listing_vals = []
    for price in [q.price for q in listing_quotes if q.price > 0]:
        if remaining.get(price, 0) > 0:
            listing_vals.append(price)
            remaining[price] -= 1
    values = recent_sold + listing_vals
    if not values:
        return 0, 0, ""
    tier = "sold+listing" if recent_sold and listing_vals else (
        "sold" if recent_sold else "listing"
    )
    return round(sum(values) / len(values)), len(values), tier


# ── 일본판 박스 ──────────────────────────────────────────────

_JP_MSRP_YEN: dict[str, int] | None = None
_JP_MSRP_PACK_YEN: dict[str, int] | None = None
_JP_MSRP_NAMES: dict[str, str] | None = None


def _load_jp_msrp() -> tuple[dict[str, int], dict[str, str]]:
    global _JP_MSRP_YEN, _JP_MSRP_PACK_YEN, _JP_MSRP_NAMES
    if _JP_MSRP_YEN is not None:
        return _JP_MSRP_YEN, _JP_MSRP_NAMES or {}
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "seeds" / "_audit_out" / "jp_msrp_sources.json"
    yen: dict[str, int] = {}
    pack_yen: dict[str, int] = {}
    names: dict[str, str] = {}
    if path.exists():
        for row in json.loads(path.read_text(encoding="utf-8")):
            code = row.get("code") or ""
            if code:
                yen[code] = int(row.get("boxJP") or 0)
                pack_yen[code] = int(row.get("packJP") or 0)
                names[code] = row.get("jpName") or ""
    _JP_MSRP_YEN = yen
    _JP_MSRP_PACK_YEN = pack_yen
    _JP_MSRP_NAMES = names
    return yen, names


def jp_pack_msrp_krw(set_code: str, rate: float = 9.5) -> int:
    _load_jp_msrp()
    pack_yen = (_JP_MSRP_PACK_YEN or {}).get(set_code.upper(), 150) or 150
    return max(500, round(pack_yen * rate))


def jp_box_msrp_krw(set_code: str, rate: float = 9.5) -> int:
    yen_map, _ = _load_jp_msrp()
    yen = yen_map.get(set_code.upper(), 5400) or 5400
    return max(5000, round(yen * rate))


def build_jp_box_search_queries(
    set_name_kr: str,
    set_code: str,
    jp_name: str = "",
) -> list[str]:
    queries: list[str] = []
    for n in _box_search_name_candidates(set_name_kr, set_code):
        base = re.sub(r"\s*ex\s*$", "", n, flags=re.I).strip()
        for label in {n, base}:
            if not label:
                continue
            queries.extend([
                f"{label} 일본판 박스",
                f"{label} 일판 박스",
                f"{label} 일본판",
                f"{label} 일판",
                f"{label} 박스",
                f"포켓몬카드 {label} 박스",
                f"포켓몬카드 {label} 일본판 박스",
                f"포켓몬카드 {label} 일판 박스",
                f"포켓몬카드 {label} 일판 미개봉",
                f"포켓몬 {label} 박스",
            ])
    if jp_name:
        queries.append(f"포켓몬카드 {jp_name} ボックス")
        queries.append(f"포켓몬 {jp_name} BOX")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _is_korean_box(title: str) -> bool:
    return any(k in title for k in KR_KEYWORDS) or "한글" in title or "한국판" in title


def is_jp_box_listing(
    title: str,
    set_name_kr: str,
    set_code: str,
    msrp_box_krw: int,
    unit_price: int = 0,
    msrp_pack_krw: int = 0,
    *,
    allow_opened: bool = False,
) -> bool:
    if not title.strip():
        return False
    if _is_buy_listing(title):
        return False
    if _is_korean_box(title):
        return False
    if not _title_matches_set(title, set_name_kr, set_code):
        return False
    if not _is_box_listing(title, unit_price, msrp_box_krw, msrp_pack_krw):
        if not _jp_box_by_price(title, unit_price, msrp_box_krw, msrp_pack_krw):
            return False
    if _looks_like_single_card(title, unit_price, msrp_box_krw, msrp_pack_krw):
        return False
    if not allow_opened and _is_opened_box(title):
        return False
    if _is_bundle_box_listing(title, set_name_kr, set_code):
        return False
    if not _is_japanese_box(title) and not _jp_box_by_price(
        title, unit_price, msrp_box_krw, msrp_pack_krw
    ):
        return False
    return True


def filter_bunjang_jp_box_listings(
    items: list[dict],
    set_name_kr: str,
    set_code: str,
    msrp_box_krw: int,
    msrp_pack_krw: int = 0,
) -> list[int]:
    """판매중 호가 가격만 (레거시 — 크림 등)."""
    _, listings = filter_bunjang_jp_box_quotes(
        items, set_name_kr, set_code, msrp_box_krw, msrp_pack_krw, verifier=None
    )
    return [q.price for q in listings]
