"""일본판이 없는 한국 한정 프로모 (TRADE_CRAWL_CRITERIA.md §16.3, §17.3).

코드 사용처:
  - crawl_promo_prices.crawl_promo_jp — JP 스킵 + prices_jp bunjang:none
  - price_search.build_promo_jp_search_queries — JP 검색어 생성 안 함
  - jp_price_search.is_raw_jp_listing — JP 매물 필터 false
"""

from __future__ import annotations

# (set_code, card_number) — 일본판 실물·시세 없음
KR_EXCLUSIVE_PROMO_KEYS = frozenset({
    ("PRM-MISC", "040/M-P"),  # MEGA Festa 2026 한국 한정 잉어킹
})


def is_kr_exclusive_promo(set_code: str, card_number: str) -> bool:
    key = ((set_code or "").upper(), (card_number or "").strip().upper())
    return key in KR_EXCLUSIVE_PROMO_KEYS
