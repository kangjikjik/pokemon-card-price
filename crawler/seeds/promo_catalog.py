"""
사용자 요청에 따른 최소화된 프로모 카탈로그.
- 스페셜·기념: CEL(기존), CEL25PK(25주년 프로모팩), CEL30(30th CELEBRATION)
- 기타 프로모: PRM-MISC (잉어킹 등 단발 프로모 카드 모음)
"""

from __future__ import annotations

from dataclasses import dataclass

MAGIKARP_PROMO_IMAGE = "https://cdn.collectory.cc/cards/kr/M-P/040_M-P.webp"


@dataclass(frozen=True)
class PromoSource:
    code: str
    collectory_id: str
    name_kr: str
    released_at: str = ""
    image_url: str = ""


@dataclass(frozen=True)
class CommemorativeSource:
    code: str
    collectory_id: str
    name_kr: str
    released_at: str = ""
    image_url: str = ""


# 기타 프로모 (단발 증정용)
PROMO_MISC = PromoSource(
    "PRM-MISC",
    "",
    "기타 프로모팩",
    "",
    MAGIKARP_PROMO_IMAGE,
)

# 25주년 프로모팩 (P 카드 + 스페셜·기념 탭)
COMMEMORATIVE_25PK = CommemorativeSource(
    "CEL25PK",
    "50e15946-2779-44eb-82c3-2446ddbaf9ac",
    "25주년 기념 프로모팩",
    "2021-10-22",
    "https://data1.pokemonkorea.co.kr/2021/10/2021-10-15_18-19-47-44100-1634289587.png",
)

COMMEMORATIVE_30CELEBRATION = CommemorativeSource(
    "CEL30",
    "bfc5bc98-87f1-46b2-b68d-e82152e744d4",
    "30주년 기념",
    "2026-09-16",
    "/set-boxes/CEL30.png",
)

COMMEMORATIVE_SOURCES: list[CommemorativeSource] = [
    COMMEMORATIVE_25PK,
    COMMEMORATIVE_30CELEBRATION,
]

PROMO_EVENT_CODES = [] # Gym, PD26 등 모두 삭제됨
COMMEMORATIVE_CODES = [s.code for s in COMMEMORATIVE_SOURCES]
PROMO_PAGE_CODES = [PROMO_MISC.code]
PROMO_PRICE_CODES = ["CEL25PK", PROMO_MISC.code]

PROMO_SOURCES = [
    PROMO_MISC,
    PromoSource(
        "CEL25PK",
        COMMEMORATIVE_25PK.collectory_id,
        COMMEMORATIVE_25PK.name_kr,
        COMMEMORATIVE_25PK.released_at,
        COMMEMORATIVE_25PK.image_url,
    ),
]
PROMO_SET_CODES = PROMO_PRICE_CODES
PROMO_BY_CODE = {s.code: s for s in PROMO_SOURCES}

# KR set_code → 유유테이 vers (일본판 프로모 — 키워드 검색 fallback)
PROMO_YUYU_VERS: dict[str, str] = {}

COLLECTORY_API = "https://collectory.cc/api"
PROMO_RARITY_RAW = frozenset({"PROMO", "P", "프로모"})

COMMEMORATIVE_ONLY_CODES = ["CEL25PK", "CEL30"]
