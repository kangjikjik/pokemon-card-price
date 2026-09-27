"""호가→거래완료 PID reconcile (TRADE_CRAWL_CRITERIA.md §13)과 이상치 재판정 (§9)."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from lib.trade_sources import (
    extract_bunjang_pid,
    is_card_detail_row,
    is_listing_detail_source,
    is_sold_detail_source,
)


def split_detail_prices(rows: list[dict]) -> tuple[list[int], list[int]]:
    """상세 행 목록 → (sold_prices, listing_prices). 동일 PID는 sold 우선."""
    sold_pids: set[str] = set()
    sold_prices: list[int] = []
    listing_prices: list[int] = []
    for row in rows:
        src = str(row.get("source") or "")
        if not is_card_detail_row(src):
            continue
        pid = extract_bunjang_pid(src)
        if not pid:
            continue
        price = int(row.get("price_krw") or 0)
        if price <= 0:
            continue
        if is_sold_detail_source(src):
            sold_pids.add(pid)
            sold_prices.append(price)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_listing_detail_source(src):
            continue
        pid = extract_bunjang_pid(src)
        if not pid or pid in sold_pids:
            continue
        price = int(row.get("price_krw") or 0)
        if price > 0:
            listing_prices.append(price)
    return sold_prices, listing_prices


def build_historical_by_card(rows: list[dict]) -> dict[int, tuple[list[int], list[int]]]:
    """DB 상세 행 → card_id별 (sold_prices, listing_prices), PID dedupe."""
    by_card: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_card_detail_row(src):
            continue
        by_card[int(row["card_id"])].append(row)
    return {
        cid: split_detail_prices(card_rows)
        for cid, card_rows in by_card.items()
    }


def _take_kept_prices(prices: list[int], remaining: Counter) -> list[int]:
    kept: list[int] = []
    for price in prices:
        price = int(price)
        if price > 0 and remaining[price] > 0:
            kept.append(price)
            remaining[price] -= 1
    return kept


def _take_kept_items(items: list[dict], remaining: Counter) -> list[dict]:
    kept: list[dict] = []
    for item in items:
        price = int(item.get("price") or 0)
        if price > 0 and remaining[price] > 0:
            kept.append(item)
            remaining[price] -= 1
    return kept


def apply_outlier_filter(
    historical_sold: list[int],
    historical_listing: list[int],
    sold_items: list[dict],
    listing_items: list[dict],
    rarity: str,
) -> tuple[list[int], list[int], list[dict], list[dict]]:
    """§9. 기존 상세를 먼저 소비하고, 탈락한 과거 가격은 평균에 다시 넣지 않는다.

    Returns: (sold_prices, listing_prices, kept_sold_items, kept_listing_items)
    """
    from lib.price_search import filter_prices_pipeline  # noqa: PLC0415

    new_sold = [int(it.get("price") or 0) for it in sold_items]
    new_listing = [int(it.get("price") or 0) for it in listing_items]
    remaining = Counter(
        filter_prices_pipeline(
            list(historical_sold) + list(historical_listing) + new_sold + new_listing,
            rarity,
        )
    )
    kept_hist_sold = _take_kept_prices(list(historical_sold), remaining)
    kept_hist_listing = _take_kept_prices(list(historical_listing), remaining)
    kept_sold_items = _take_kept_items(sold_items, remaining)
    kept_listing_items = _take_kept_items(listing_items, remaining)
    sold_prices = kept_hist_sold + [int(it["price"]) for it in kept_sold_items]
    listing_prices = kept_hist_listing + [int(it["price"]) for it in kept_listing_items]
    return sold_prices, listing_prices, kept_sold_items, kept_listing_items


def outlier_detail_ids_to_drop(
    rows: list[dict],
    rarity_by_card: dict[int, str],
    *,
    kr_floor_by_card: dict[int, int] | None = None,
) -> list[int]:
    """이미 저장된 상세 행 중 §9(그리고 JP는 한국판 하한)에서 탈락하는 id."""
    from lib.price_search import filter_prices_pipeline  # noqa: PLC0415

    floors = kr_floor_by_card or {}
    by_card: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_card_detail_row(src) or not row.get("id"):
            continue
        by_card[int(row["card_id"])].append(row)

    drop_ids: list[int] = []
    for cid, card_rows in by_card.items():
        floor = int(floors.get(cid) or 0)
        eligible: list[dict] = []
        for row in card_rows:
            price = int(row.get("price_krw") or 0)
            if floor > 0 and price < floor:
                drop_ids.append(int(row["id"]))
                continue
            eligible.append(row)
        sold_rows = [
            row for row in eligible if is_sold_detail_source(str(row.get("source") or ""))
        ]
        sold_pids = {
            extract_bunjang_pid(str(row.get("source") or ""))
            for row in sold_rows
            if extract_bunjang_pid(str(row.get("source") or ""))
        }
        listing_rows = []
        for row in eligible:
            src = str(row.get("source") or "")
            if not is_listing_detail_source(src):
                continue
            pid = extract_bunjang_pid(src)
            if pid and pid in sold_pids:
                drop_ids.append(int(row["id"]))
                continue
            listing_rows.append(row)
        prices = [int(row.get("price_krw") or 0) for row in sold_rows + listing_rows]
        remaining = Counter(filter_prices_pipeline(prices, rarity_by_card.get(cid, "")))
        for row in sold_rows + listing_rows:
            price = int(row.get("price_krw") or 0)
            if price > 0 and remaining[price] > 0:
                remaining[price] -= 1
                continue
            drop_ids.append(int(row["id"]))
    return drop_ids


def _delete_ids(sb: Any, table: str, ids: list[int]) -> int:
    if not ids:
        return 0
    deleted = 0
    for i in range(0, len(ids), 200):
        batch = ids[i : i + 200]
        sb.table(table).delete().in_("id", batch).execute()
        deleted += len(batch)
    return deleted


def reconcile_card_rows(
    sb: Any,
    table: str,
    card_ids: list[int],
    rows: list[dict],
    existing: list[dict] | None = None,
) -> tuple[list[dict], int]:
    """
    저장 전 §13 reconcile.
    Returns: (filtered_rows, deleted_listing_count)
    """
    if not rows:
        return rows, 0

    if existing is None and card_ids:
        existing = (
            sb.table(table)
            .select("id,card_id,source")
            .in_("card_id", card_ids)
            .execute()
            .data
            or []
        )
    existing = existing or []

    existing_sold_pids: dict[int, set[str]] = defaultdict(set)
    listing_ids_by_key: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row in existing:
        src = str(row.get("source") or "")
        cid = int(row["card_id"])
        pid = extract_bunjang_pid(src)
        if not pid:
            continue
        if is_sold_detail_source(src):
            existing_sold_pids[cid].add(pid)
        elif is_listing_detail_source(src):
            listing_ids_by_key[(cid, pid)].append(int(row["id"]))

    new_sold_pids: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_sold_detail_source(src):
            continue
        cid = int(row["card_id"])
        pid = extract_bunjang_pid(src)
        if pid:
            new_sold_pids[cid].add(pid)

    delete_ids: list[int] = []
    for cid, pids in new_sold_pids.items():
        for pid in pids:
            delete_ids.extend(listing_ids_by_key.get((cid, pid), []))
    deleted = _delete_ids(sb, table, delete_ids)

    filtered: list[dict] = []
    batch_sold_pids: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_card_detail_row(src):
            filtered.append(row)
            continue
        cid = int(row["card_id"])
        pid = extract_bunjang_pid(src)
        if not pid:
            filtered.append(row)
            continue
        if is_sold_detail_source(src):
            known = (
                existing_sold_pids.get(cid, set())
                | batch_sold_pids.get(cid, set())
            )
            if pid in known:
                continue
            batch_sold_pids[cid].add(pid)
            filtered.append(row)
            continue
        if is_listing_detail_source(src):
            sold_set = (
                existing_sold_pids.get(cid, set())
                | batch_sold_pids.get(cid, set())
                | new_sold_pids.get(cid, set())
            )
            if pid in sold_set:
                continue
            filtered.append(row)
    return filtered, deleted


def reconcile_box_rows(
    sb: Any,
    set_ids: list[int],
    region: str,
    rows: list[dict],
    existing: list[dict] | None = None,
) -> tuple[list[dict], int]:
    """박스 prices_box 저장 전 §13 reconcile."""
    if not rows:
        return rows, 0

    if existing is None and set_ids:
        existing = (
            sb.table("prices_box")
            .select("id,set_id,region,source")
            .in_("set_id", set_ids)
            .eq("region", region)
            .execute()
            .data
            or []
        )
    existing = existing or []

    existing_sold_pids: dict[tuple[int, str], set[str]] = defaultdict(set)
    listing_ids_by_key: dict[tuple[int, str, str], list[int]] = defaultdict(list)
    for row in existing:
        src = str(row.get("source") or "")
        sid = int(row["set_id"])
        reg = str(row.get("region") or "")
        pid = extract_bunjang_pid(src)
        if not pid:
            continue
        key = (sid, reg)
        if is_sold_detail_source(src):
            existing_sold_pids[key].add(pid)
        elif is_listing_detail_source(src):
            listing_ids_by_key[(sid, reg, pid)].append(int(row["id"]))

    new_sold_pids: dict[tuple[int, str], set[str]] = defaultdict(set)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_sold_detail_source(src):
            continue
        sid = int(row["set_id"])
        reg = str(row.get("region") or region)
        pid = extract_bunjang_pid(src)
        if pid:
            new_sold_pids[(sid, reg)].add(pid)

    delete_ids: list[int] = []
    for key, pids in new_sold_pids.items():
        sid, reg = key
        for pid in pids:
            delete_ids.extend(listing_ids_by_key.get((sid, reg, pid), []))
    deleted = _delete_ids(sb, "prices_box", delete_ids)

    filtered: list[dict] = []
    batch_sold_pids: dict[tuple[int, str], set[str]] = defaultdict(set)
    for row in rows:
        src = str(row.get("source") or "")
        if not is_card_detail_row(src):
            filtered.append(row)
            continue
        sid = int(row["set_id"])
        reg = str(row.get("region") or region)
        pid = extract_bunjang_pid(src)
        if not pid:
            filtered.append(row)
            continue
        key = (sid, reg)
        if is_sold_detail_source(src):
            known = existing_sold_pids.get(key, set()) | batch_sold_pids.get(key, set())
            if pid in known:
                continue
            batch_sold_pids[key].add(pid)
            filtered.append(row)
            continue
        if is_listing_detail_source(src):
            sold_set = (
                existing_sold_pids.get(key, set())
                | batch_sold_pids.get(key, set())
                | new_sold_pids.get(key, set())
            )
            if pid in sold_set:
                continue
            filtered.append(row)
    return filtered, deleted


def build_box_historical_quotes(
    history_rows: list[dict],
    source_prefix: str,
) -> tuple[list[Any], list[Any]]:
    """박스 DB 상세 행 → (sold_quotes, listing_quotes), PID dedupe."""
    from lib.box_price_search import VerifiedBoxQuote  # noqa: PLC0415
    from lib.trade_sources import extract_bunjang_update_time  # noqa: PLC0415

    sold_raw: list[dict] = []
    listing_raw: list[dict] = []
    for row in history_rows:
        src = str(row.get("source") or "")
        if not src.startswith(f"{source_prefix}:"):
            continue
        if is_sold_detail_source(src):
            sold_raw.append(row)
        elif is_listing_detail_source(src):
            listing_raw.append(row)

    sold_pids = {
        extract_bunjang_pid(str(r.get("source") or ""))
        for r in sold_raw
    }
    sold_pids.discard(None)

    def _quote(row: dict) -> VerifiedBoxQuote:
        src = str(row.get("source") or "")
        return VerifiedBoxQuote(
            price=int(row["price_krw"]),
            updated_at=extract_bunjang_update_time(src),
            pid=extract_bunjang_pid(src) or "",
        )

    sold_quotes = [_quote(r) for r in sold_raw]
    listing_quotes = [
        _quote(r) for r in listing_raw
        if extract_bunjang_pid(str(r.get("source") or "")) not in sold_pids
    ]
    return sold_quotes, listing_quotes


def purge_listing_rows_with_sold_duplicate(sb: Any, table: str) -> int:
    """백필: sold PID가 있는 listing 상세 행 일괄 삭제."""
    offset = 0
    page = 1000
    sold_index: dict[int, set[str]] = defaultdict(set)
    listing_rows: list[dict] = []
    while True:
        batch = (
            sb.table(table)
            .select("id,card_id,source")
            .range(offset, offset + page - 1)
            .execute()
            .data
            or []
        )
        if not batch:
            break
        for row in batch:
            src = str(row.get("source") or "")
            pid = extract_bunjang_pid(src)
            if not pid:
                continue
            cid = int(row["card_id"])
            if is_sold_detail_source(src):
                sold_index[cid].add(pid)
            elif is_listing_detail_source(src):
                listing_rows.append(row)
        if len(batch) < page:
            break
        offset += page

    delete_ids = [
        int(row["id"])
        for row in listing_rows
        if extract_bunjang_pid(str(row.get("source") or ""))
        in sold_index.get(int(row["card_id"]), set())
    ]
    return _delete_ids(sb, table, delete_ids)


def purge_box_listing_rows_with_sold_duplicate(sb: Any) -> int:
    """prices_box — sold PID가 있는 listing 상세 행 일괄 삭제."""
    offset = 0
    page = 1000
    sold_index: dict[tuple[int, str], set[str]] = defaultdict(set)
    listing_rows: list[dict] = []
    while True:
        batch = (
            sb.table("prices_box")
            .select("id,set_id,region,source")
            .range(offset, offset + page - 1)
            .execute()
            .data
            or []
        )
        if not batch:
            break
        for row in batch:
            src = str(row.get("source") or "")
            pid = extract_bunjang_pid(src)
            if not pid:
                continue
            key = (int(row["set_id"]), str(row.get("region") or ""))
            if is_sold_detail_source(src):
                sold_index[key].add(pid)
            elif is_listing_detail_source(src):
                listing_rows.append(row)
        if len(batch) < page:
            break
        offset += page

    delete_ids = [
        int(row["id"])
        for row in listing_rows
        if extract_bunjang_pid(str(row.get("source") or ""))
        in sold_index.get(
            (int(row["set_id"]), str(row.get("region") or "")),
            set(),
        )
    ]
    return _delete_ids(sb, "prices_box", delete_ids)
