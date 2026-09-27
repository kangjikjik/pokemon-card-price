"""증분·catch-up 크롤 일자 (TRADE_CRAWL_CRITERIA.md §14)."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))
STATE_PATH = Path(__file__).resolve().parent.parent / "seeds" / "_trade_crawl_state.json"


def kst_today() -> date:
    return datetime.now(KST).date()


def kst_day_bounds(d: date) -> tuple[int, int]:
    """KST 달력 하루 [start, end) Unix timestamp."""
    start = datetime.combine(d, datetime.min.time(), tzinfo=KST)
    end = start + timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())


def is_kst_day(update_time: int, day: date) -> bool:
    if not update_time:
        return False
    start, end = kst_day_bounds(day)
    return start <= int(update_time) < end


def is_in_incremental_days(update_time: int, days: list[date]) -> bool:
    if not update_time or not days:
        return False
    return any(is_kst_day(update_time, d) for d in days)


def load_crawl_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_crawl_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def read_last_crawl_kst(sb: Any | None = None) -> date | None:
    """상태 파일 → 없으면 DB fetched_at 최대값(KST)으로 추정."""
    raw = load_crawl_state().get("last_crawl_kst")
    if raw:
        try:
            return date.fromisoformat(str(raw))
        except ValueError:
            pass
    if sb is None:
        return None
    latest: date | None = None
    for table in ("prices_kr", "prices_jp", "prices_box"):
        rows = (
            sb.table(table)
            .select("fetched_at")
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows or not rows[0].get("fetched_at"):
            continue
        try:
            iso = str(rows[0]["fetched_at"]).replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso).astimezone(KST).date()
        except ValueError:
            continue
        if latest is None or dt > latest:
            latest = dt
    return latest


def compute_catch_up_days(sb: Any, *, today: date | None = None) -> list[date]:
    """마지막 크롤(KST) 다음날 ~ today 포함."""
    today = today or kst_today()
    last = read_last_crawl_kst(sb)
    if last is None:
        return [today - timedelta(days=1)]
    if last >= today:
        return []
    out: list[date] = []
    d = last + timedelta(days=1)
    while d <= today:
        out.append(d)
        d += timedelta(days=1)
    return out


def get_incremental_days(argv: list[str] | None = None, sb: Any | None = None) -> list[date] | None:
    """
    None — 전체 재크롤(일자 필터 없음)
    [] — catch-up 대상 없음(이미 최신)
    [date, ...] — 해당 KST 일자만 수집
    """
    argv = argv if argv is not None else sys.argv
    if "--catch-up" in argv:
        if sb is None:
            from utils.db import get_supabase  # noqa: PLC0415
            sb = get_supabase()
        return compute_catch_up_days(sb)
    if "--previous-day" in argv:
        return [kst_today() - timedelta(days=1)]
    return None


def is_incremental_mode(days: list[date] | None) -> bool:
    return days is not None


def format_days(days: list[date]) -> str:
    if not days:
        return "(없음)"
    if len(days) == 1:
        return days[0].isoformat()
    return f"{days[0].isoformat()} ~ {days[-1].isoformat()} ({len(days)}일)"


def print_incremental_banner(days: list[date] | None, *, last_crawl: date | None = None) -> None:
    if days is None:
        return
    last_s = last_crawl.isoformat() if last_crawl else "?"
    if not days:
        print(f"=== catch-up: 마지막 크롤 {last_s} — 오늘({kst_today()})까지 이미 반영됨, 스킵 ===")
        return
    print(f"=== 증분 크롤: {format_days(days)} (마지막 크롤 KST: {last_s}) ===")


def exit_if_caught_up(days: list[date] | None, last_crawl: date | None = None) -> None:
    """catch-up 대상 0일이면 조기 종료."""
    if days is not None and len(days) == 0:
        print_incremental_banner(days, last_crawl=last_crawl)
        sys.exit(0)


def mark_crawl_kst_complete(today: date | None = None) -> None:
    """파이프라인 성공 후 last_crawl_kst = today."""
    today = today or kst_today()
    state = load_crawl_state()
    state["last_crawl_kst"] = today.isoformat()
    state["updated_at"] = datetime.now(KST).isoformat(timespec="seconds")
    save_crawl_state(state)


def forward_incremental_flags(cmd: list[str], argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv
    if "--catch-up" in argv:
        cmd.append("--catch-up")
    elif "--previous-day" in argv:
        cmd.append("--previous-day")
