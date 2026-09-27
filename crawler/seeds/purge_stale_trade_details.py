"""
180일 초과 번개장터 상세 거래 행 삭제 + SNKRDUNK 레거시 row 정리.

정책: crawler/TRADE_CRAWL_CRITERIA.md §11

  python purge_stale_trade_details.py          # 드라이런
  python purge_stale_trade_details.py --apply
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.trade_sources import (  # noqa: E402
    is_legacy_snk_source,
    is_stale_detail,
    is_trade_detail_source,
)
from utils.db import get_supabase  # noqa: E402

APPLY = "--apply" in sys.argv
PAGE = 1000


def _purge_table(sb, table: str) -> tuple[int, int]:
    """Returns (stale_deleted, snk_deleted)."""
    stale_ids: list[int] = []
    snk_ids: list[int] = []
    offset = 0
    while True:
        rows = (
            sb.table(table)
            .select("id, source, fetched_at")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
            or []
        )
        if not rows:
            break
        for row in rows:
            src = str(row.get("source") or "")
            rid = int(row["id"])
            if is_legacy_snk_source(src):
                snk_ids.append(rid)
                continue
            if is_trade_detail_source(src) and is_stale_detail(
                src, row.get("fetched_at"),
            ):
                stale_ids.append(rid)
        if len(rows) < PAGE:
            break
        offset += PAGE

    deleted_stale = _delete_ids(sb, table, stale_ids)
    deleted_snk = _delete_ids(sb, table, snk_ids)
    return deleted_stale, deleted_snk


def _delete_ids(sb, table: str, ids: list[int]) -> int:
    if not ids or not APPLY:
        return len(ids)
    deleted = 0
    for i in range(0, len(ids), 200):
        batch = ids[i : i + 200]
        sb.table(table).delete().in_("id", batch).execute()
        deleted += len(batch)
    return deleted


def main() -> None:
    sb = get_supabase()
    mode = "[APPLY]" if APPLY else "[DRY]"
    print(f"{mode} TRADE §11 — 180일 초과 상세 행 + SNKRDUNK 레거시 정리")

    totals = {"stale": 0, "snk": 0}
    for table in ("prices_kr", "prices_jp"):
        stale, snk = _purge_table(sb, table)
        print(f"  {table}: stale={stale}, snk={snk}")
        totals["stale"] += stale
        totals["snk"] += snk

    box_stale, box_snk = _purge_box(sb)
    print(f"  prices_box: stale={box_stale}, snk={box_snk}")
    totals["stale"] += box_stale
    totals["snk"] += box_snk

    print(
        f"합계: stale={totals['stale']}, snk={totals['snk']}"
        + ("" if APPLY else " — 반영: --apply")
    )


def _purge_box(sb) -> tuple[int, int]:
    stale_ids: list[int] = []
    snk_ids: list[int] = []
    offset = 0
    while True:
        rows = (
            sb.table("prices_box")
            .select("id, source, fetched_at")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
            or []
        )
        if not rows:
            break
        for row in rows:
            src = str(row.get("source") or "")
            rid = int(row["id"])
            if is_legacy_snk_source(src):
                snk_ids.append(rid)
                continue
            if is_trade_detail_source(src) and is_stale_detail(
                src, row.get("fetched_at"),
            ):
                stale_ids.append(rid)
        if len(rows) < PAGE:
            break
        offset += PAGE
    return _delete_ids(sb, "prices_box", stale_ids), _delete_ids(sb, "prices_box", snk_ids)


if __name__ == "__main__":
    main()
