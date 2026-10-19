"""일별 시세 스냅샷 저장 — 과거 이력 유지, 같은 날(KST)은 교체."""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from lib.trade_reconcile import reconcile_box_rows, reconcile_card_rows

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


_DETAIL_PREFIXES = (
    "sold:bunjang:",
    "listing:bunjang:",
    "bunjang:sold:",
    "bunjang:listing:",
    "bunjang-jp:sold:",
    "bunjang-jp:listing:",
)


def snapshot_day(days: list[date] | None) -> date:
    """이번 크롤이 남길 날짜. catch-up이면 끝 날, 아니면 프로세스 시작 시각의 KST 오늘."""
    if days:
        return days[-1]
    return datetime.now(KST).date()


def crawl_fetched_at(day: date) -> str:
    """예약 크롤일 정오(KST). 한국판·일본판이 같은 날짜로 남는다."""
    noon = datetime(day.year, day.month, day.day, 12, 0, tzinfo=KST)
    return noon.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_detail_source(source: str) -> bool:
    return source.startswith(_DETAIL_PREFIXES)


def stamp_summary_fetched_at(rows: list[dict], day: date) -> None:
    """요약 행만 크롤일로 찍는다. 거래 상세의 매물 시각은 그대로 둔다."""
    iso = crawl_fetched_at(day)
    for row in rows:
        if _is_detail_source(str(row.get("source") or "")):
            continue
        row["fetched_at"] = iso


def _bounds_for(crawl_day: date | None) -> tuple[str, str]:
    if crawl_day is None:
        return kst_day_bounds_utc()
    noon = datetime(crawl_day.year, crawl_day.month, crawl_day.day, 12, 0, tzinfo=KST)
    return kst_day_bounds_utc(noon)


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
    crawl_day: date | None = None,
) -> tuple[int, int]:
    """
    card_ids 대상 카드의 오늘(KST) 스냅샷만 지우고 rows를 insert.
    과거 날짜 행은 유지. 오늘 시세가 없는 카드는 과거 이력을 지우지 않음.

    Returns: (deleted_today, inserted)
    """
    if not card_ids:
        return 0, 0

    rows, _ = reconcile_card_rows(sb, table, card_ids, rows)
    if crawl_day is not None:
        stamp_summary_fetched_at(rows, crawl_day)

    start, end = _bounds_for(crawl_day)
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
    crawl_day: date | None = None,
) -> tuple[int, int]:
    """
    set_ids 대상 세트의 오늘(KST) 박스 스냅샷만 지우고 rows를 insert.
    region: 'KR' | 'JP'
    """
    if not set_ids:
        return 0, 0

    rows, _ = reconcile_box_rows(sb, set_ids, region, rows)
    if crawl_day is not None:
        stamp_summary_fetched_at(rows, crawl_day)

    start, end = _bounds_for(crawl_day)
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
    crawl_day: date | None = None,
) -> tuple[int, int]:
    """Update today's summaries while preserving every existing detail row."""
    if not card_ids:
        return 0, 0

    if crawl_day is not None:
        stamp_summary_fetched_at(rows, crawl_day)
    start, end = _bounds_for(crawl_day)
    batch = 200
    existing = (
        sb.table(table)
        .select("id,card_id,source")
        .in_("card_id", card_ids)
        .execute()
        .data
        or []
    )
    rows, _ = reconcile_card_rows(sb, table, card_ids, rows, existing=existing)
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
    crawl_day: date | None = None,
) -> tuple[int, int]:
    """Box equivalent of save_incremental_snapshots."""
    if not set_ids:
        return 0, 0

    if crawl_day is not None:
        stamp_summary_fetched_at(rows, crawl_day)
    start, end = _bounds_for(crawl_day)
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
    rows, _ = reconcile_box_rows(sb, set_ids, region, rows, existing=existing)
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


def _parse_utc(iso: str) -> datetime:
    text = str(iso).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _kst_date(moment: datetime) -> date:
    return moment.astimezone(KST).date()


def _is_card_summary(source: str, price: int) -> bool:
    from lib.trade_sources import is_card_detail_row  # noqa: PLC0415

    if price <= 0 or is_card_detail_row(source):
        return False
    return not source.startswith("bunjang:none")


def _iter_table_rows(sb: Any, table: str, columns: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        batch = (
            sb.table(table)
            .select(columns)
            .order("id")
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def crawl_day_by_moment(moments: list[datetime]) -> dict[datetime, date]:
    """자정을 넘긴 한 번의 크롤은 끝난 날짜 하나로 묶는다."""
    ordered = sorted(set(moments))
    if not ordered:
        return {}
    clusters: list[list[datetime]] = [[ordered[0]]]
    for moment in ordered[1:]:
        if moment - clusters[-1][-1] <= timedelta(hours=8):
            clusters[-1].append(moment)
        else:
            clusters.append([moment])
    mapped: dict[datetime, date] = {}
    for cluster in clusters:
        day = _kst_date(cluster[-1])
        for moment in cluster:
            mapped[moment] = day
    return mapped


def _summary_source_for(details: list[dict]) -> str:
    from lib.trade_sources import is_listing_detail_source, is_sold_detail_source  # noqa: PLC0415

    has_sold = any(is_sold_detail_source(str(row.get("source") or "")) for row in details)
    has_listing = any(is_listing_detail_source(str(row.get("source") or "")) for row in details)
    if has_sold and has_listing:
        return "sold+listing:bunjang"
    if has_sold:
        return "sold:bunjang"
    return "listing:bunjang"


def ensure_crawl_day_summaries(
    sb: Any,
    table: str,
    card_ids: list[int],
    crawl_day: date,
) -> int:
    """매물이 있는 카드는 이번 크롤일 점을 남긴다. 매물이 없으면 만들지 않는다."""
    from lib.trade_sources import is_card_detail_row  # noqa: PLC0415

    if not card_ids:
        return 0
    iso = crawl_fetched_at(crawl_day)
    columns = "id,card_id,price_krw,source,fetched_at"
    if table == "prices_jp":
        columns += ",price_jpy"
    rows = _load_rows_for_cards(sb, table, card_ids, columns)
    by_card: dict[int, list[dict]] = {}
    for row in rows:
        by_card.setdefault(int(row["card_id"]), []).append(row)

    inserts: list[dict] = []
    updates: list[tuple[int, dict]] = []
    for card_id, card_rows in by_card.items():
        details = [
            row for row in card_rows
            if is_card_detail_row(str(row.get("source") or "")) and int(row.get("price_krw") or 0) > 0
        ]
        if not details:
            continue
        prices = [int(row["price_krw"]) for row in details]
        payload: dict[str, Any] = {
            "price_krw": round(sum(prices) / len(prices)),
            "source": _summary_source_for(details),
            "fetched_at": iso,
        }
        if table == "prices_jp":
            jpy = [int(row.get("price_jpy") or 0) for row in details if int(row.get("price_jpy") or 0) > 0]
            if jpy:
                payload["price_jpy"] = round(sum(jpy) / len(jpy))
        same_day = [
            row for row in card_rows
            if _is_card_summary(str(row.get("source") or ""), int(row.get("price_krw") or 0))
            and row.get("fetched_at")
            and _kst_date(_parse_utc(str(row["fetched_at"]))) == crawl_day
        ]
        if same_day:
            latest = max(same_day, key=lambda row: str(row.get("fetched_at") or ""))
            updates.append((int(latest["id"]), payload))
            continue
        payload["card_id"] = card_id
        inserts.append(payload)

    for row_id, payload in updates:
        sb.table(table).update(payload).eq("id", row_id).execute()
    for i in range(0, len(inserts), 200):
        sb.table(table).insert(inserts[i : i + 200]).execute()
    return len(updates) + len(inserts)


def _load_rows_for_cards(sb: Any, table: str, card_ids: list[int], columns: str) -> list[dict]:
    rows: list[dict] = []
    for i in range(0, len(card_ids), 20):
        chunk = card_ids[i : i + 20]
        offset = 0
        while True:
            batch = (
                sb.table(table)
                .select(columns)
                .in_("card_id", chunk)
                .order("id")
                .range(offset, offset + 999)
                .execute()
                .data
                or []
            )
            rows.extend(batch)
            if len(batch) < 1000:
                break
            offset += 1000
    return rows


def align_summary_crawl_days(sb: Any, table: str, day_by_moment: dict[datetime, date]) -> tuple[int, int]:
    """이미 저장된 요약을 크롤일 정오로 맞추고, 매물이 있는데 빠진 크롤일은 직전 시세로 채운다."""
    from lib.trade_sources import is_card_detail_row  # noqa: PLC0415

    columns = "id,card_id,price_krw,source,fetched_at"
    if table == "prices_jp":
        columns += ",price_jpy"
    rows = _iter_table_rows(sb, table, columns)
    summaries: dict[int, list[dict]] = {}
    has_detail: set[int] = set()
    for row in rows:
        source = str(row.get("source") or "")
        price = int(row.get("price_krw") or 0)
        card_id = int(row["card_id"])
        if is_card_detail_row(source) and price > 0:
            has_detail.add(card_id)
        if _is_card_summary(source, price) and row.get("fetched_at"):
            summaries.setdefault(card_id, []).append(row)

    crawl_days = sorted(set(day_by_moment.values()))
    moved = 0
    for card_rows in summaries.values():
        for row in card_rows:
            moment = _parse_utc(str(row["fetched_at"]))
            day = day_by_moment.get(moment) or _kst_date(moment)
            row["crawl_day"] = day
            if _kst_date(moment) == day:
                continue
            target = crawl_fetched_at(day)
            sb.table(table).update({"fetched_at": target}).eq("id", int(row["id"])).execute()
            row["fetched_at"] = target
            moved += 1

    inserts: list[dict] = []
    for card_id in sorted(has_detail):
        card_rows = sorted(summaries.get(card_id, []), key=lambda row: str(row.get("fetched_at") or ""))
        if not card_rows:
            continue
        owned = {row["crawl_day"] for row in card_rows}
        first = min(owned)
        carried: dict | None = None
        for day in crawl_days:
            if day < first:
                continue
            existing = [row for row in card_rows if row["crawl_day"] == day]
            if existing:
                carried = max(existing, key=lambda row: str(row.get("fetched_at") or ""))
                continue
            if carried is None:
                continue
            payload = {
                "card_id": card_id,
                "price_krw": int(carried["price_krw"]),
                "source": carried.get("source") or "sold+listing:bunjang",
                "fetched_at": crawl_fetched_at(day),
            }
            if table == "prices_jp" and int(carried.get("price_jpy") or 0) > 0:
                payload["price_jpy"] = int(carried["price_jpy"])
            inserts.append(payload)
            carried = payload
    for i in range(0, len(inserts), 200):
        sb.table(table).insert(inserts[i : i + 200]).execute()
    return moved, len(inserts)
