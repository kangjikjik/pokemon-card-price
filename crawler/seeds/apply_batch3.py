"""3배치 15팩 — kr_sets + web lib 반영"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from apply_batch1 import ensure_kr_sets_footer, to_krset, write_kr_sets, write_set_msrp
from batch3_verified import BATCH3_VERIFIED
from kr_sets import KR_SETS
from revert_featured_55 import write_constants, write_set_images, write_set_names

WEB = Path(__file__).resolve().parents[2] / "web" / "lib"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    by_code = {s.code: s for s in KR_SETS}
    for v in BATCH3_VERIFIED:
        by_code[v.code] = to_krset(v)
    merged = sorted(by_code.values(), key=lambda s: s.released_at, reverse=True)
    n = len(merged)
    write_kr_sets(merged)
    ensure_kr_sets_footer()

    const_path = WEB / "constants.ts"
    text = const_path.read_text(encoding="utf-8")
    text = re.sub(r"export const FEATURED_SET_LIMIT = \d+;", f"export const FEATURED_SET_LIMIT = {n};", text)
    const_path.write_text(text, encoding="utf-8")

    write_constants([s.code for s in merged])
    write_set_names(merged)
    write_set_images(merged)
    write_set_msrp(merged)
    print(f"batch3 applied — featured {n}")


if __name__ == "__main__":
    main()
