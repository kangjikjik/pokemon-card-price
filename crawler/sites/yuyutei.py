"""
遊々亭 (yuyu-tei.jp) 일본 카드 판매 시세 크롤러
httpx로 페이지를 가져와 정규식으로 파싱합니다.
"""
import re
import asyncio
import httpx
from utils.db import (
    get_all_cards,
    match_card_by_number,
    match_card_by_name,
    save_price_jp,
    parse_price_jpy,
)

BASE_URL = "https://yuyu-tei.jp"
SELL_SEARCH = f"{BASE_URL}/sell/poc/s/search"

# DB에 있는 카드의 일본어 이름 키워드로 검색
SEARCH_KEYWORDS = [
    "リザードンex",
    "ミュウex",
    "ピカチュウ",
    "モヤモヤ",      # 이온 (Iono)
    "ギラティナ",
    "ルギア",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# HTML 구조 기반 정규식:
# <span class="...text-center...">201/165</span>
# <a ...><h4 class="text-primary fw-bold">リザードンex</h4></a>
# <strong class="d-block text-end ...">79,800 円</strong>
CARD_PATTERN = re.compile(
    r'text-center[^>]*>(\d+/\d+)</span>.*?<h4[^>]*>([^<]+)</h4>.*?<strong[^>]*>\s*([\d,]+)\s*円',
    re.DOTALL,
)


def parse_yuyutei_page(text: str) -> list[dict]:
    """
    유유테이 판매 페이지 HTML에서 카드 정보를 파싱합니다.
    반환: [{"card_number": "201/165", "name_jp": "リザードンex", "price_jpy": 79800}]
    """
    results = []
    for match in CARD_PATTERN.finditer(text):
        card_number = match.group(1).strip()
        name_jp = match.group(2).strip()
        price_text = match.group(3).strip()

        price_jpy = parse_price_jpy(price_text)
        if price_jpy and price_jpy > 0:
            results.append({
                "card_number": card_number,
                "name_jp": name_jp,
                "price_jpy": price_jpy,
            })
    return results


async def fetch_yuyutei(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    """키워드로 유유테이 판매 검색 페이지를 가져와 파싱합니다."""
    try:
        resp = await client.get(
            SELL_SEARCH,
            params={"search_word": keyword},
            timeout=15,
        )
        resp.raise_for_status()
        return parse_yuyutei_page(resp.text)
    except Exception as e:
        print(f"[유유테이] '{keyword}' 가져오기 실패: {e}")
        return []


async def crawl_yuyutei(exchange_rate: float) -> int:
    """
    유유테이에서 카드 판매 시세를 수집하고 DB에 저장합니다.
    exchange_rate: JPY→KRW 환율 (예: 9.5)
    반환: 저장된 시세 건수
    """
    print("[유유테이] 크롤링 시작")
    all_cards = get_all_cards()
    if not all_cards:
        print("[유유테이] DB에 카드 데이터 없음 — 종료")
        return 0

    saved = 0
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        for keyword in SEARCH_KEYWORDS:
            items = await fetch_yuyutei(keyword, client)
            print(f"[유유테이] '{keyword}' → {len(items)}건 파싱")

            for item in items:
                # 카드 번호로 먼저 매칭, 실패 시 이름으로 매칭
                card = match_card_by_number(item["card_number"], all_cards)
                if not card:
                    card = match_card_by_name(item["name_jp"], all_cards)
                if not card:
                    continue

                price_jpy = item["price_jpy"]
                price_krw = round(price_jpy * exchange_rate)
                if save_price_jp(card["id"], price_jpy, price_krw, "yuyutei"):
                    saved += 1

            await asyncio.sleep(2)  # 서버 부하 방지

    print(f"[유유테이] 완료 — {saved}건 저장")
    return saved
