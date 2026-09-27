"""포켓몬 카드 레어도 → 정렬용 rank (높을수록 상위) — web/lib/rarity.ts 와 동기화"""

RARITY_ALIASES: dict[str, str] = {
    "UR-ex": "SR",
    "IR": "AR",
    "Futuristic Rare": "FUR",
    "Pikachu Rare": "PKR",
}

# 히트: UR/HR/… > PR > SR > … > RR
RARITY_RANK: dict[str, int] = {
    "FUR": 32,
    "MUR": 30,
    "UR": 29,
    "BWR": 28,
    "SAR": 27,
    "CC": 27,
    "PKR": 26,
    "MA": 25,
    "SR": 24,
    "ACE": 23,
    "AR": 22,
    "SSR": 22,
    "HR": 21,
    "CSR": 20,
    "PR": 19,
    "CHR": 18,
    "RRR": 17,
    "A": 16,
    "K": 15,
    "S": 14,
    "TR": 13,
    "H": 11,
    "RR": 10,
    "R": 3,
    "U": 2,
    "C": 1,
    "P": 0,
}

RARITY_ORDER = sorted(RARITY_RANK.keys(), key=lambda r: -RARITY_RANK[r])


def normalize_rarity(rarity: str | None) -> str:
    r = (rarity or "").strip()
    return RARITY_ALIASES.get(r, r)


def rank_for_rarity(rarity: str | None) -> int:
    return RARITY_RANK.get(normalize_rarity(rarity), 0)


# web/lib/rarity.ts MIN_DISPLAY_RARITY_RANK 와 동기화
MIN_DISPLAY_RARITY_RANK = 10
_SKIP_DISPLAY = {"U", "C", "SA", "N", "CM", "UM", "PROMO", "R", "M", "RM"}


def is_promo_rarity(rarity: str | None) -> bool:
    return normalize_rarity(rarity) == "P"


def is_displayable_rarity(rarity: str | None) -> bool:
    norm = normalize_rarity(rarity)
    if is_promo_rarity(norm):
        return True
    if norm in _SKIP_DISPLAY:
        return False
    return rank_for_rarity(norm) >= MIN_DISPLAY_RARITY_RANK
