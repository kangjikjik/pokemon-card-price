"""번개장터 거래 source 문자열·상세 행 판별 (TRADE_CRAWL_CRITERIA.md)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

SOLD_MAX_AGE_DAYS = 180
# 카드 한 장·한 지역에서 거래완료와 판매중 호가를 합친 상세 행 상한.
MAX_CARD_TRADE_ROWS = 50

BUNJANG_NONE = "bunjang:none"
BUNJANG_NONE_NO_DETAIL = "bunjang:none:no_detail"

_CARD_DETAIL_RE = re.compile(r"^(sold|listing):bunjang:\d+(:\d+)?$")
_BOX_DETAIL_RE = re.compile(r"^bunjang(-jp)?:(sold|listing):\d+(:\d+)?$")
_LEGACY_SNK_RE = re.compile(r"^sold:snkrdunk:\d+")


def box_none_source(prefix: str, *, no_detail: bool = False) -> str:
    return f"{prefix}:none:no_detail" if no_detail else f"{prefix}:none"


def is_card_detail_source(source: str) -> bool:
    return bool(_CARD_DETAIL_RE.match(source or ""))


def is_box_detail_source(source: str) -> bool:
    return bool(_BOX_DETAIL_RE.match(source or ""))


def is_trade_detail_source(source: str) -> bool:
    return is_card_detail_source(source) or is_box_detail_source(source)


def is_legacy_snk_source(source: str) -> bool:
    return bool(_LEGACY_SNK_RE.match(source or ""))


def extract_bunjang_pid(source: str) -> str | None:
    """카드·박스 상세 source에서 번개장터 상품 PID 추출."""
    src = source or ""
    parts = src.split(":")
    if is_card_detail_source(src) and len(parts) >= 3 and parts[1] == "bunjang":
        return parts[2] if parts[2].isdigit() else None
    if is_box_detail_source(src) and len(parts) >= 3:
        return parts[2] if parts[2].isdigit() else None
    return None


def extract_bunjang_update_time(source: str) -> int:
    """source에 Unix timestamp가 있으면 반환, 없으면 0."""
    parts = (source or "").split(":")
    if len(parts) >= 4:
        try:
            return int(parts[3])
        except ValueError:
            return 0
    return 0


def is_sold_detail_source(source: str) -> bool:
    src = source or ""
    if src.startswith("sold:bunjang:"):
        return True
    parts = src.split(":")
    return is_box_detail_source(src) and len(parts) >= 2 and parts[1] == "sold"


def is_listing_detail_source(source: str) -> bool:
    src = source or ""
    if src.startswith("listing:bunjang:"):
        return True
    parts = src.split(":")
    return is_box_detail_source(src) and len(parts) >= 2 and parts[1] == "listing"


def is_card_detail_row(source: str) -> bool:
    return is_sold_detail_source(source) or is_listing_detail_source(source)


def detail_timestamp(source: str, fetched_at: str | None) -> datetime | None:
    """상세 행의 거래·게시 시각. source에 TS 없으면 fetched_at 사용."""
    src = source or ""
    parts = src.split(":")
    ts: int | None = None
    if is_card_detail_source(src) and len(parts) >= 4:
        try:
            ts = int(parts[3])
        except ValueError:
            ts = None
    elif is_box_detail_source(src) and len(parts) >= 4:
        try:
            ts = int(parts[3])
        except ValueError:
            ts = None
    if ts and ts > 0:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if fetched_at:
        try:
            normalized = fetched_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def is_stale_detail(source: str, fetched_at: str | None, *, max_age_days: int = SOLD_MAX_AGE_DAYS) -> bool:
    """180일 초과 상세 행 여부 (§11)."""
    if not is_trade_detail_source(source):
        return False
    dt = detail_timestamp(source, fetched_at)
    if dt is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return dt < cutoff
