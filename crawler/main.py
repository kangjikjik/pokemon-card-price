"""
Cardory 시세 크롤 진입점 (레거시).

일일 시세 수집은 seeds 배치 스크립트를 사용한다.
정책: crawler/TRADE_CRAWL_CRITERIA.md

  cd crawler/seeds
  python purge_stale_trade_details.py --apply
  python reconcile_listing_to_sold.py --apply
  python crawl_prices_batch.py --apply --daily --all --catch-up
  python crawl_prices_batch_jp.py --apply --all --catch-up
  python crawl_box_prices_batch.py --apply --all --catch-up
  python crawl_box_prices_batch.py --apply --all --region JP --catch-up
"""
from __future__ import annotations

import sys


def main() -> None:
    print("일일 시세 크롤은 crawler/seeds/crawl_*_batch.py 를 사용하세요.")
    print("기준 문서: crawler/TRADE_CRAWL_CRITERIA.md")
    sys.exit(1)


if __name__ == "__main__":
    main()
