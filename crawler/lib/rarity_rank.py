"""포켓몬 카드 레어도 → 정렬용 rank (높을수록 상위) — web/lib/rarity.ts 와 동기화"""

RARITY_ALIASES: dict[str, str] = {
    "UR-ex": "SR",
    "IR": "AR",
    "RM": "RR",
    "Shining": "SL",
    "SHINING": "SL",
}

# 히트: UR/HR/… > PR > SR > … > RR
RARITY_RANK: dict[str, int] = {
    "FUR": 30,
    "MA": 29,
    "MUR": 28,
    "BWR": 27,
    "ACE": 26,
    "UR": 25,
    "SSR": 24,
    "HR": 23,
    "SAR": 22,
    "CSR": 21,
    "AR": 20,
    "PR": 19,
    "SR": 18,
    "CHR": 17,
    "RRR": 16,
    "A": 15,
    "K": 14,
    "S": 13,
    "TR": 12,
    "SL": 11,
    "H": 10,
    "RR": 9,
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
