"""증분·catch-up 크롤 일자 (TRADE_CRAWL_CRITERIA.md §14).

자동 크롤 간격은 4일(§15). 이 모듈은 마지막 크롤 다음날~오늘을 그대로 돌려주므로
간격이 늘어나도 일자 계산을 따로 자르지 않는다. Actions schedule은 4일 cron이다.
"""
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


# 홈 순서 표에 같이 둔다. period_end 는 1970-01-01 이라 조회 구간 계산에 안 쓰인다.
CRAWL_KST_KIND = "crawl_kst"
_CRAWL_KST_UNUSED_END = "1970-01-01"


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag not in argv:
        return None
    index = argv.index(flag)
    if index + 1 >= len(argv):
        return None
    return argv[index + 1]


def explicit_catch_up_days(argv: list[str] | None = None) -> list[date] | None:
    """`--catch-up-from` ~ `--catch-up-to` 가 있으면 그 구간. 없으면 None."""
    argv = argv if argv is not None else sys.argv
    start_s = _arg_value(argv, "--catch-up-from")
    end_s = _arg_value(argv, "--catch-up-to")
    if not start_s and not end_s:
        return None
    if not start_s or not end_s:
        raise SystemExit("--catch-up-from 과 --catch-up-to 는 함께 필요합니다.")
    start = date.fromisoformat(start_s)
    end = date.fromisoformat(end_s)
    if end < start:
        return []
    out: list[date] = []
    day = start
    while day <= end:
        out.append(day)
        day += timedelta(days=1)
    return out


def read_db_last_crawl_kst(sb: Any) -> date | None:
    """가격 저장 시각이 아니라, 파이프라인이 끝나며 적어 둔 마지막 크롤일."""
    try:
        rows = (
            sb.table("home_highlights")
            .select("period_start")
            .eq("kind", CRAWL_KST_KIND)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None
    if not rows or not rows[0].get("period_start"):
        return None
    try:
        return date.fromisoformat(str(rows[0]["period_start"])[:10])
    except ValueError:
        return None


def read_last_crawl_kst(sb: Any | None = None) -> date | None:
    """DB에 적어 둔 마지막 크롤일 → 없으면 상태 파일.

    시세 `fetched_at` 은 카드를 저장한 시각이라 마지막 크롤일로 쓰지 않는다.
    한 장이라도 오늘 저장되면 나머지 세트가 건너뛰어지기 때문이다.
    """
    if sb is not None:
        stored = read_db_last_crawl_kst(sb)
        if stored is not None:
            return stored
    raw = load_crawl_state().get("last_crawl_kst")
    if raw:
        try:
            return date.fromisoformat(str(raw))
        except ValueError:
            pass
    return None


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
    explicit = explicit_catch_up_days(argv)
    if explicit is not None:
        return explicit
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


def write_db_last_crawl_kst(sb: Any, day: date) -> None:
    sb.table("home_highlights").delete().eq("kind", CRAWL_KST_KIND).execute()
    sb.table("home_highlights").insert({
        "kind": CRAWL_KST_KIND,
        "rank": 1,
        "card_id": None,
        "set_id": None,
        "view_count": 0,
        "period_start": day.isoformat(),
        "period_end": _CRAWL_KST_UNUSED_END,
    }).execute()


def mark_crawl_kst_complete(today: date | None = None, sb: Any | None = None) -> None:
    """카드·박스 전부가 끝난 뒤에만 last_crawl_kst = today."""
    today = today or kst_today()
    state = load_crawl_state()
    state["last_crawl_kst"] = today.isoformat()
    state["updated_at"] = datetime.now(KST).isoformat(timespec="seconds")
    save_crawl_state(state)
    if sb is None:
        from utils.db import get_supabase  # noqa: PLC0415
        sb = get_supabase()
    write_db_last_crawl_kst(sb, today)


def forward_incremental_flags(
    cmd: list[str],
    argv: list[str] | None = None,
    days: list[date] | None = None,
) -> None:
    """자식 프로세스에는 이미 정한 날짜만 넘긴다. 저장 뒤에 다시 계산하지 않는다."""
    if days is not None:
        if days:
            cmd.extend([
                "--catch-up-from",
                days[0].isoformat(),
                "--catch-up-to",
                days[-1].isoformat(),
            ])
        return
    argv = argv if argv is not None else sys.argv
    explicit = explicit_catch_up_days(argv)
    if explicit:
        cmd.extend([
            "--catch-up-from",
            explicit[0].isoformat(),
            "--catch-up-to",
            explicit[-1].isoformat(),
        ])
        return
    if "--catch-up" in argv:
        cmd.append("--catch-up")
    elif "--previous-day" in argv:
        cmd.append("--previous-day")
