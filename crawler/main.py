"""
PokéPrice 크롤러 메인 진입점
12시간마다 실행되어 한국/일본 카드 시세를 수집하고 DB에 저장합니다.

실행 방법:
  cd crawler
  python main.py
"""
import asyncio
import sys
from utils.exchange import get_exchange_rate
from utils.db import save_exchange_rate
from sites.bunjang import crawl_bunjang
from sites.yuyutei import crawl_yuyutei


async def main():
    print("=" * 50)
    print("  PokéPrice Crawler 시작")
    print("=" * 50)

    # 1. 환율 조회 및 저장
    print("\n[1/3] 환율 조회 중...")
    rate = await get_exchange_rate()
    save_exchange_rate(rate)
    print(f"  → JPY→KRW: {rate}")

    # 2. 한국판 시세 수집 (번개장터)
    print("\n[2/3] 번개장터 크롤링 중...")
    kr_count = await crawl_bunjang()
    print(f"  → {kr_count}건 저장")

    # 3. 일본판 시세 수집 (유유테이)
    print("\n[3/3] 유유테이 크롤링 중...")
    jp_count = await crawl_yuyutei(rate)
    print(f"  → {jp_count}건 저장")

    print("\n" + "=" * 50)
    print(f"  완료! KR: {kr_count}건 / JP: {jp_count}건")
    print("=" * 50)


if __name__ == "__main__":
    # 특정 사이트만 실행하고 싶을 때: python main.py bunjang / python main.py yuyutei
    if len(sys.argv) > 1:
        site = sys.argv[1].lower()
        if site == "bunjang":
            asyncio.run(crawl_bunjang())
        elif site == "yuyutei":

            async def run_yuyutei():
                rate = await get_exchange_rate()
                await crawl_yuyutei(rate)

            asyncio.run(run_yuyutei())
        else:
            print(f"알 수 없는 사이트: {site}. 'bunjang' 또는 'yuyutei'를 입력하세요.")
    else:
        asyncio.run(main())
