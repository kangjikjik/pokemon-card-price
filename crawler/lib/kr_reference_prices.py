"""한국판 대표 시세 참조 — JP 오매칭 하한 (TRADE_CRAWL_CRITERIA.md §2, §17.3).

사용처: crawl_set_prices_jp.py, crawl_promo_prices.py (JP).
"""

from __future__ import annotations

from typing import Any


def load_kr_reference_prices(sb: Any, card_ids: list[int]) -> dict[int, int]:
    """카드별 한국판 요약 시세. PID 상세 행은 제외."""
    if not card_ids:
        return {}
    rows = (
        sb.table("prices_kr")
        .select("card_id,price_krw,source")
        .in_("card_id", card_ids)
        .gt("price_krw", 0)
        .execute()
        .data
        or []
    )
    refs: dict[int, int] = {}
    for row in rows:
        source = str(row.get("source") or "")
        if source.startswith("sold:bunjang:") or source.startswith("listing:bunjang:"):
            continue
        refs[int(row["card_id"])] = int(row["price_krw"])
    return refs
