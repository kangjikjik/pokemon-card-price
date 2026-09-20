# -*- coding: utf-8 -*-
"""MG7 box filter rejection reason."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.box_price_search import (
    _is_buy_listing,
    _is_bundle_box_listing,
    _is_japanese_box,
    _is_korean_box,
    _is_opened_box,
    _is_box_listing,
    _jp_box_by_price,
    _looks_like_single_card,
    _title_matches_set,
    is_jp_box_listing,
)
from kr_sets import KR_BY_CODE

meta = KR_BY_CODE["MG7"]
MSRP = 120000
PACK = 4000

TITLES = [
    ("포켓몬 카드 스톰에메랄da 일판 1box 슈링크 있음", 130000),
    ("(슈링크O) 포켓몬카드 스톰에메랄da 미개봉 1박스", 51000),
    ("포켓몬카드 스톰에메랄da 미개봉 슈링크O 1박스", 53000),
    ("포켓몬 카드 스톰에메랄da 일본판 1box 슈링크 있음", 130000),
]


def why(title: str, price: int) -> None:
    print(f"\n--- {title[:60]} @ {price:,} ---")
    checks = [
        ("buy", _is_buy_listing(title)),
        ("korean_box", _is_korean_box(title)),
        ("set_match", _title_matches_set(title, meta.name_kr, "MG7")),
        ("box_listing", _is_box_listing(title, price, MSRP, PACK)),
        ("jp_by_price", _jp_box_by_price(title, price, MSRP, PACK)),
        ("single_card", _looks_like_single_card(title, price, MSRP, PACK)),
        ("opened", _is_opened_box(title)),
        ("bundle", _is_bundle_box_listing(title, meta.name_kr, "MG7")),
        ("jp_box", _is_japanese_box(title)),
        ("FINAL", is_jp_box_listing(title, meta.name_kr, "MG7", MSRP, price, PACK, allow_opened=True)),
    ]
    for name, val in checks:
        mark = "FAIL" if (name != "FINAL" and val and name in ("buy", "korean_box", "single_card", "opened", "bundle")) else ""
        mark = "FAIL" if (name != "FINAL" and not val and name in ("set_match", "FINAL")) else mark
        mark = "FAIL" if (name != "FINAL" and not val and name in ("box_listing", "jp_by_price") and not _is_box_listing(title, price, MSRP, PACK) and not _jp_box_by_price(title, price, MSRP, PACK)) else mark
        print(f"  {name}: {val} {mark}")


def main() -> None:
    for t, p in TITLES:
        why(t, p)


if __name__ == "__main__":
    main()
