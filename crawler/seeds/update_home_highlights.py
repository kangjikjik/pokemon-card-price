"""
마지막 홈 갱신 다음날부터 오늘까지 카드·세트 조회수로 홈 순서를 바꾼다.

주간 핫카드 1장, 인기 급상승 4장, 주요 세트 4개.
조회가 없으면 기존 순서를 유지한다. 칸이 비면 web/lib/constants.ts 폴백으로 채운다.

  python update_home_highlights.py
  python update_home_highlights.py --apply
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.crawl_incremental import CRAWL_KST_KIND, kst_today, mark_crawl_kst_complete  # noqa: E402
from utils.db import get_supabase  # noqa: E402

APPLY = "--apply" in sys.argv
PAGE = 1000
TRENDING_SLOTS = 4
SET_SLOTS = 4

# web/lib/constants.ts 폴백과 같게 유지한다.
FALLBACK_HOT = 9150
FALLBACK_TRENDING = [11554, 11553, 9694, 11551]
FALLBACK_SETS = [256, 252, 86, 67]


def _missing_table(exc: Exception) -> bool:
    text = str(exc)
    return "PGRST205" in text or "42P01" in text


def _rows(sb, table: str, id_col: str, start: date | None, end: date) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        query = sb.table(table).select(f"{id_col},view_date,view_count")
        if start is not None:
            query = query.gte("view_date", start.isoformat())
        batch = (
            query.lte("view_date", end.isoformat())
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
            or []
        )
        out.extend(batch)
        if len(batch) < PAGE:
            return out
        offset += PAGE


def _totals(rows: list[dict], id_col: str) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in rows:
        raw_id = row.get(id_col)
        if raw_id is None:
            continue
        totals[int(raw_id)] = totals.get(int(raw_id), 0) + int(row.get("view_count") or 0)
    return totals


def _ranked(totals: dict[int, int]) -> list[int]:
    return sorted(totals, key=lambda item_id: (-totals[item_id], item_id))


def _fill(ranked: list[int], need: int, fallback: list[int]) -> list[int]:
    chosen: list[int] = []
    seen: set[int] = set()
    for item_id in [*ranked, *fallback]:
        if item_id in seen:
            continue
        seen.add(item_id)
        chosen.append(item_id)
        if len(chosen) >= need:
            break
    return chosen


def _period_start(sb) -> date | None:
    rows = (
        sb.table("home_highlights")
        .select("period_end")
        .neq("kind", CRAWL_KST_KIND)
        .order("period_end", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows or not rows[0].get("period_end"):
        return None
    return date.fromisoformat(str(rows[0]["period_end"])) + timedelta(days=1)


def _write(sb, kind: str, records: list[dict]) -> None:
    sb.table("home_highlights").delete().eq("kind", kind).execute()
    if records:
        sb.table("home_highlights").insert(records).execute()


def main() -> int:
    sb = get_supabase()
    today = kst_today()
    try:
        start = _period_start(sb)
    except Exception as exc:
        if _missing_table(exc):
            print("home_highlights 테이블이 없습니다. add_home_highlights.sql 을 먼저 실행하세요.")
            return 0
        raise

    if start is not None and start > today:
        print(f"홈 순서는 이미 {today.isoformat()}까지 반영되어 있습니다.")
        return _finish(sb)

    try:
        card_rows = _rows(sb, "card_view_days", "card_id", start, today)
        set_rows = _rows(sb, "set_view_days", "set_id", start, today)
    except Exception as exc:
        if _missing_table(exc):
            print("조회 테이블이 없습니다. add_home_highlights.sql 을 먼저 실행하세요.")
            return 0
        raise

    card_totals = _totals(card_rows, "card_id")
    set_totals = _totals(set_rows, "set_id")
    window = f"{(start or today).isoformat()} ~ {today.isoformat()}"
    print(f"조회 구간 {window}: 카드 {len(card_totals)}종, 세트 {len(set_totals)}종")

    if not card_totals and not set_totals:
        print("이 구간에 조회가 없어 홈 순서를 유지합니다.")
        return _finish(sb)

    dates = [str(row["view_date"]) for row in [*card_rows, *set_rows] if row.get("view_date")]
    period_start = start or date.fromisoformat(min(dates))
    period_end = today

    if card_totals:
        ordered = _fill(
            _ranked(card_totals),
            1 + TRENDING_SLOTS,
            [FALLBACK_HOT, *FALLBACK_TRENDING],
        )
        hot_id = ordered[0]
        trending_ids = [item_id for item_id in ordered[1:] if item_id != hot_id][:TRENDING_SLOTS]
        print(f"주간 핫카드 {hot_id} ({card_totals.get(hot_id, 0)}회)")
        print("인기 급상승 " + ", ".join(f"{item_id}({card_totals.get(item_id, 0)})" for item_id in trending_ids))
        if APPLY:
            _write(sb, "hot_card", [{
                "kind": "hot_card",
                "rank": 1,
                "card_id": hot_id,
                "set_id": None,
                "view_count": card_totals.get(hot_id, 0),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            }])
            _write(sb, "trending_card", [
                {
                    "kind": "trending_card",
                    "rank": index,
                    "card_id": item_id,
                    "set_id": None,
                    "view_count": card_totals.get(item_id, 0),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                }
                for index, item_id in enumerate(trending_ids, start=1)
            ])
    else:
        print("카드 조회가 없어 핫카드·급상승은 유지합니다.")

    if set_totals:
        set_ids = _fill(_ranked(set_totals), SET_SLOTS, FALLBACK_SETS)
        print("주요 세트 " + ", ".join(f"{item_id}({set_totals.get(item_id, 0)})" for item_id in set_ids))
        if APPLY:
            _write(sb, "featured_set", [
                {
                    "kind": "featured_set",
                    "rank": index,
                    "card_id": None,
                    "set_id": item_id,
                    "view_count": set_totals.get(item_id, 0),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                }
                for index, item_id in enumerate(set_ids, start=1)
            ])
    else:
        print("세트 조회가 없어 주요 세트는 유지합니다.")

    return _finish(sb)


def _finish(sb) -> int:
    if not APPLY:
        print("저장하지 않았습니다. 반영하려면 --apply")
        return 0
    mark_crawl_kst_complete(sb=sb)
    print(f"마지막 크롤일 {kst_today().isoformat()} 저장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
