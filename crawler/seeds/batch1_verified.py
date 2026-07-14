"""1배치(MG4a/MG2a/MG1b) — pokemoncard.co.kr 검증값"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedSet:
    code: str
    name_kr: str
    released_at: str
    box_image_kr: str
    bs_code: str
    collectory_id: str
    msrp_pack_kr: int
    msrp_box_kr: int
    pokemoncard_page: int


# probe_page_dates.py + find_page_by_needle 검증 (2026-07-10)
BATCH1_VERIFIED: list[VerifiedSet] = [
    VerifiedSet(
        "MG4a", "MEGA 드림 ex", "2026-01-23",
        "https://data1.pokemonkorea.co.kr/2025/12/2025-12-30_11-00-50-12772-1767060050.png",
        "BS2025015", "ede55e39-375f-43ba-b325-5a8d3d46cd29",
        5000, 50000, 859,
    ),
    VerifiedSet(
        "MG2a", "화이트플레어", "2025-08-01",
        "https://data1.pokemonkorea.co.kr/2025/07/2025-07-10_16-51-40-50682-1752133900.png",
        "BS2025008", "7dfcee5a-5e1a-4886-9694-44020932b47b",
        2000, 40000, 796,
    ),
    VerifiedSet(
        "MG1b", "로켓단의 영광", "2025-06-20",
        "https://data1.pokemonkorea.co.kr/2025/05/2025-05-28_17-24-50-69720-1748420690.png",
        "BS2025006", "40147c73-4a1e-412c-aa48-ee697f9c3e14",
        1000, 30000, 785,
    ),
]

BATCH1_CODES = [s.code for s in BATCH1_VERIFIED]
