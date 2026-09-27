"""
§13 백필 — sold PID가 있는 listing 상세 행 일괄 삭제.

  python reconcile_listing_to_sold.py          # 드라이런
  python reconcile_listing_to_sold.py --apply
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.trade_reconcile import (  # noqa: E402
    purge_box_listing_rows_with_sold_duplicate,
    purge_listing_rows_with_sold_duplicate,
)

APPLY = "--apply" in sys.argv


def main() -> None:
    from utils.db import get_supabase  # noqa: E402

    sb = get_supabase()
    mode = "[APPLY]" if APPLY else "[DRY]"
    print(f"{mode} TRADE §13 — listing/sold PID 중복 정리")

    if not APPLY:
        print("  (드라이런 — 카운트만 표시, DB 변경 없음)")
        # 드라이런은 reconcile 모듈이 delete를 skip하므로 apply 없이는 0
        print("  반영: --apply")

    kr = purge_listing_rows_with_sold_duplicate(sb, "prices_kr") if APPLY else 0
    jp = purge_listing_rows_with_sold_duplicate(sb, "prices_jp") if APPLY else 0
    box = purge_box_listing_rows_with_sold_duplicate(sb) if APPLY else 0

    if APPLY:
        print(f"  prices_kr listing 삭제: {kr}")
        print(f"  prices_jp listing 삭제: {jp}")
        print(f"  prices_box listing 삭제: {box}")
        print(f"합계: {kr + jp + box}")


if __name__ == "__main__":
    main()
