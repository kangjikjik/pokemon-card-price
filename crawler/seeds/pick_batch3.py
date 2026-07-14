"""3배치 15팩 후보 — SM7a 이전 미포함 팩"""
from __future__ import annotations

import httpx

from analyze_timeline_gaps import eligible
from gap_sets import CODE_BY_NAME
from kr_sets import FEATURED_SET_CODES

BATCH3_CODES = [
    "SM6b", "SM6a", "SM6", "SM5+", "SM5", "SM4+", "SM4", "SM4a",
    "SM2+", "SM1+", "SM1M", "SM1C", "CP6", "XY11", "XY9",
]

PAGE_HINTS = {
    "SM6b": 140, "SM6a": 137, "SM6": 132, "SM5+": 130, "SM5": 128,
    "SM4+": 124, "SM4": 124, "SM4a": 120, "SM2+": 118, "SM1+": 110,
    "SM1M": 99, "SM1C": 99, "CP6": 89, "XY11": 83, "XY9": 62,
}


def fetch_batch3_sets() -> list[tuple[str, str, str, str]]:
    featured = set(FEATURED_SET_CODES)
    by_code = {}
    for e in eligible:
        name = e.get("name_ko") or ""
        if name not in CODE_BY_NAME:
            continue
        code, name_kr = CODE_BY_NAME[name]
        if code not in BATCH3_CODES or code in featured:
            continue
        by_code[code] = (
            code,
            name_kr,
            e["id"],
            e.get("set_code_ko", ""),
        )
    out = [by_code[c] for c in BATCH3_CODES if c in by_code]
    return out


def main():
    sets = fetch_batch3_sets()
    print(f"batch3={len(sets)}")
    for i, (code, name, cid, bs) in enumerate(sets, 1):
        print(f"{i:2}. {code:6} {name[:28]:28} {bs:14} p{PAGE_HINTS.get(code,0)} {cid}")


if __name__ == "__main__":
    main()
