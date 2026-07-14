"""4배치 12팩 후보"""
from __future__ import annotations

from analyze_timeline_gaps import eligible
from gap_sets import CODE_BY_NAME
from kr_sets import FEATURED_SET_CODES

BATCH4_CODES = [
    "XY8a", "XY7", "XY6", "XY5a", "XY5b", "XY4", "XY3", "XY2",
    "EBB1", "XY5", "XY3a", "BW4",
]

PAGE_HINTS = {
    "XY8a": 65,
    "XY7": 50,
    "XY6": 47,
    "XY5a": 44,
    "XY5b": 44,
    "XY4": 40,
    "XY3": 36,
    "XY2": 33,
    "EBB1": 30,
    "XY5": 25,
    "XY3a": 9,
    "BW4": 13,
}


def fetch_batch4_sets() -> list[tuple[str, str, str, str]]:
    featured = set(FEATURED_SET_CODES)
    by_code = {}
    for e in eligible:
        name = e.get("name_ko") or ""
        if name not in CODE_BY_NAME:
            continue
        code, name_kr = CODE_BY_NAME[name]
        if code not in BATCH4_CODES or code in featured:
            continue
        by_code[code] = (code, name_kr, e["id"], e.get("set_code_ko", ""))
    return [by_code[c] for c in BATCH4_CODES if c in by_code]
