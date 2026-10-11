"""전체 크롤 전에 GitHub Actions에서 시크릿, DB, 번개 검색만 확인한다.

저장은 하지 않는다. 하나라도 실패하면 종료 코드 1.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.bunjang_card_price import fetch_bunjang_items  # noqa: E402
from utils.db import get_supabase  # noqa: E402

TABLES = ("card_view_days", "set_view_days", "home_highlights")


def main() -> int:
    failed = False
    sb = get_supabase()
    print("시크릿으로 데이터베이스 클라이언트 생성")

    try:
        rows = sb.table("cards").select("id").limit(1).execute().data or []
    except Exception as exc:
        print(f"cards 조회 실패: {exc}")
        return 1
    if not rows:
        print("cards 행이 없습니다.")
        failed = True
    else:
        print(f"cards 연결 확인 id={rows[0]['id']}")

    for table in TABLES:
        try:
            sb.table(table).select("*").limit(1).execute()
        except Exception as exc:
            print(f"{table} 조회 실패: {exc}")
            failed = True
            continue
        print(f"{table} 테이블 확인")

    try:
        items = fetch_bunjang_items("샤로다 SAR")
    except Exception as exc:
        print(f"번개 검색 실패: {exc}")
        return 1
    usable = [item for item in items if item.get("pid") and item.get("status") in ("0", "3")]
    print(f"번개 검색 {len(items)}건, 판매중·판매완료 {len(usable)}건")
    if not usable:
        failed = True

    if failed:
        print("검사 실패")
        return 1
    print("검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
