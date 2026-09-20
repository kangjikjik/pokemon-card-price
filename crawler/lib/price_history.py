"""일별 시세 스냅샷 저장 — 과거 이력 유지, 같은 날(KST)은 교체."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

KST = timezone(timedelta(hours=9))

_MAX_RETRIES = 5
_RETRY_DELAY_SEC = 3


def _execute_with_retry(fn: Callable[[], Any]) -> Any:
    """Supabase 일시 네트워크 오류 시 재시도."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt + 1 >= _MAX_RETRIES:
                break
            time.sleep(_RETRY_DELAY_SEC * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def kst_day_bounds_utc(
    when: datetime | None = None,
) -> tuple[str, str]:
    """KST 기준 당일 [start, end) 를 UTC ISO 문자열로 반환."""
    now = when or datetime.now(KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    else:
        now = now.astimezone(KST)
    start_kst = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_kst = start_kst + timedelta(days=1)
    start_utc = start_kst.astimezone(timezone.utc)
    end_utc = end_kst.astimezone(timezone.utc)
    return (
        start_utc.isoformat().replace("+00:00", "Z"),
        end_utc.isoformat().replace("+00:00", "Z"),
    )


def save_daily_snapshots(
    sb: Any,
    table: str,
    card_ids: list[int],
    rows: list[dict],
) -> tuple[int, int]:
    """
    card_ids 대상 카드의 오늘(KST) 스냅샷만 지우고 rows를 insert.
    과거 날짜 행은 유지. 오늘 시세가 없는 카드는 과거 이력을 지우지 않음.

    Returns: (deleted_today, inserted)
    """
    if not card_ids:
        return 0, 0

    start, end = kst_day_bounds_utc()
    deleted = 0
    # Supabase in_ 필터 한도 대비 배치
    batch = 200
    for i in range(0, len(card_ids), batch):
        chunk = card_ids[i : i + batch]
        res = _execute_with_retry(
            lambda c=chunk: sb.table(table)
            .delete()
            .in_("card_id", c)
            .gte("fetched_at", start)
            .lt("fetched_at", end)
            .execute()
        )
        deleted += len(res.data or [])

    inserted = 0
    if rows:
        for i in range(0, len(rows), batch):
            chunk = rows[i : i + batch]
            _execute_with_retry(
                lambda c=chunk: sb.table(table).insert(c).execute()
            )
            inserted += len(chunk)
    return deleted, inserted


def save_daily_box_snapshots(
    sb: Any,
    set_ids: list[int],
    region: str,
    rows: list[dict],
) -> tuple[int, int]:
    """
    set_ids 대상 세트의 오늘(KST) 박스 스냅샷만 지우고 rows를 insert.
    region: 'KR' | 'JP'
    """
    if not set_ids:
        return 0, 0

    start, end = kst_day_bounds_utc()
    deleted = 0
    batch = 200
    for i in range(0, len(set_ids), batch):
        chunk = set_ids[i : i + batch]
        res = _execute_with_retry(
            lambda c=chunk: sb.table("prices_box")
            .delete()
            .in_("set_id", c)
            .eq("region", region)
            .gte("fetched_at", start)
            .lt("fetched_at", end)
            .execute()
        )
        deleted += len(res.data or [])

    inserted = 0
    if rows:
        for i in range(0, len(rows), batch):
            chunk = rows[i : i + batch]
            _execute_with_retry(
                lambda c=chunk: sb.table("prices_box").insert(c).execute()
            )
            inserted += len(chunk)
    return deleted, inserted


def save_incremental_snapshots(
    sb: Any,
    table: str,
    card_ids: list[int],
    rows: list[dict],
) -> tuple[int, int]:
    """Update today's summaries while preserving every existing detail row."""
    if not card_ids:
        return 0, 0

    start, end = kst_day_bounds_utc()
    batch = 200
    existing = (
        sb.table(table)
        .select("id,card_id,source")
        .in_("card_id", card_ids)
        .execute()
        .data
        or []
    )
    existing_sources = {
        (int(row["card_id"]), str(row.get("source") or ""))
        for row in existing
    }
    today = (
        sb.table(table)
        .select("id,source")
        .in_("card_id", card_ids)
        .gte("fetched_at", start)
        .lt("fetched_at", end)
        .execute()
        .data
        or []
    )
    summary_ids = [
        row["id"]
        for row in today
        if not str(row.get("source") or "").startswith(
            ("sold:bunjang:", "listing:bunjang:")
        )
    ]
    deleted = 0
    for i in range(0, len(summary_ids), batch):
        result = _execute_with_retry(
            lambda chunk=summary_ids[i : i + batch]: sb.table(table)
            .delete()
            .in_("id", chunk)
            .execute()
        )
        deleted += len(result.data or [])

    new_rows = [
        row for row in rows
        if (
            not str(row.get("source") or "").startswith(("sold:bunjang:", "listing:bunjang:"))
            or (int(row["card_id"]), str(row.get("source") or "")) not in existing_sources
        )
    ]
    inserted = 0
    for i in range(0, len(new_rows), batch):
        chunk = new_rows[i : i + batch]
        _execute_with_retry(lambda c=chunk: sb.table(table).insert(c).execute())
        inserted += len(chunk)
    return deleted, inserted


def save_incremental_box_snapshots(
    sb: Any,
    set_ids: list[int],
    region: str,
    rows: list[dict],
) -> tuple[int, int]:
    """Box equivalent of save_incremental_snapshots."""
    if not set_ids:
        return 0, 0

    start, end = kst_day_bounds_utc()
    batch = 200
    existing = (
        sb.table("prices_box")
        .select("id,set_id,region,source")
        .in_("set_id", set_ids)
        .eq("region", region)
        .execute()
        .data
        or []
    )
    existing_sources = {
        (int(row["set_id"]), str(row.get("region") or ""), str(row.get("source") or ""))
        for row in existing
    }
    today = (
        sb.table("prices_box")
        .select("id,source")
        .in_("set_id", set_ids)
        .eq("region", region)
        .gte("fetched_at", start)
        .lt("fetched_at", end)
        .execute()
        .data
        or []
    )
    summary_ids = [
        row["id"]
        for row in today
        if not str(row.get("source") or "").startswith(
            ("bunjang:sold:", "bunjang:listing:", "bunjang-jp:sold:", "bunjang-jp:listing:")
        )
    ]
    deleted = 0
    for i in range(0, len(summary_ids), batch):
        result = _execute_with_retry(
            lambda chunk=summary_ids[i : i + batch]: sb.table("prices_box")
            .delete()
            .in_("id", chunk)
            .execute()
        )
        deleted += len(result.data or [])

    new_rows = [
        row for row in rows
        if (
            not str(row.get("source") or "").startswith(
                ("bunjang:sold:", "bunjang:listing:", "bunjang-jp:sold:", "bunjang-jp:listing:")
            )
            or (
                int(row["set_id"]),
                str(row.get("region") or ""),
                str(row.get("source") or ""),
            ) not in existing_sources
        )
    ]
    inserted = 0
    for i in range(0, len(new_rows), batch):
        chunk = new_rows[i : i + batch]
        _execute_with_retry(lambda c=chunk: sb.table("prices_box").insert(c).execute())
        inserted += len(chunk)
    return deleted, inserted
