"""
번개장터 포켓몬 카드 시세 크롤러
번개장터 내부 JSON API를 httpx로 호출합니다.
"""
import re
import asyncio
import httpx
from utils.db import (
    get_all_cards,
    match_card_by_number,
    match_card_by_name,
    save_price_kr,
    parse_price_krw,
)

# 번개장터 내부 검색 API (앱이 사용하는 엔드포인트)
BUNJANG_API = "https://api.bunjang.co.kr/api/1/find_v2.json"

# 검색 키워드 목록 (카드 이름 + 레어도)
SEARCH_KEYWORDS = [
    "포켓몬카드 리자몽 SAR",
    "포켓몬카드 뮤 UR",
    "포켓몬카드 피카츄 AR",
    "포켓몬카드 모야모 SAR",
    "포켓몬카드 기라티나 SA",
    "포켓몬카드 루기아 SA",
    "포켓몬카드 SAR",
    "포켓몬카드 UR",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Pixel 4) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "https://m.bunjang.co.kr/",
    "Origin": "https://m.bunjang.co.kr",
}

# 카드 번호 추출 패턴 (예: "201/165", "096/071")
CARD_NUMBER_RE = re.compile(r"\b(\d{3}/\d{3})\b")

# 카드 이름 → DB 카드 이름 매핑 (번개장터 제목에서 추출 보조)
NAME_ALIASES: dict[str, str] = {
    "리자몽": "리자몽 ex",
    "뮤": "뮤 ex",
    "피카츄": "피카츄",
    "피카츄레": "피카츄",
    "모야모": "모야모",
    "기라티나": "기라티나 V",
    "루기아": "루기아 V",
}


def extract_card_number(title: str) -> str | None:
    """판매 제목에서 카드 번호(예: 201/165)를 추출합니다."""
    m = CARD_NUMBER_RE.search(title)
    return m.group(1) if m else None


def extract_card_name(title: str) -> str | None:
    """판매 제목에서 카드 이름을 추출합니다."""
    for alias, canonical in NAME_ALIASES.items():
        if alias in title:
            return canonical
    return None


def is_valid_card_listing(title: str, price: int) -> bool:
    """포켓몬 카드 단품 거래인지 검증합니다."""
    title_lower = title.lower()

    # 박스/팩 거래 제외
    if any(w in title for w in ["박스", "팩", "덱", "앨범", "바인더", "슬리브", "다량", "대량"]):
        return False

    # 너무 낮거나 비정상적인 가격 제외
    if price < 1000 or price > 10_000_000:
        return False

    return True


async def fetch_bunjang(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    """번개장터 API에서 키워드 검색 결과를 가져옵니다."""
    try:
        resp = await client.get(
            BUNJANG_API,
            params={
                "q": keyword,
                "order": "date",
                "n": "50",
                "page": "0",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("list", [])
    except Exception as e:
        print(f"[번개장터] '{keyword}' API 실패: {e}")
        return []


async def crawl_bunjang() -> int:
    """
    번개장터에서 포켓몬 카드 단품 시세를 수집하고 DB에 저장합니다.
    반환: 저장된 시세 건수
    """
    print("[번개장터] 크롤링 시작")
    all_cards = get_all_cards()
    if not all_cards:
        print("[번개장터] DB에 카드 데이터 없음 — 종료")
        return 0

    saved = 0
    seen_pids: set[str] = set()  # 중복 방지

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        for keyword in SEARCH_KEYWORDS:
            items = await fetch_bunjang(keyword, client)
            print(f"[번개장터] '{keyword}' → {len(items)}개 결과")

            for item in items:
                pid = str(item.get("pid", ""))
                if pid in seen_pids:
                    continue
                seen_pids.add(pid)

                title = item.get("name", "")
                price_str = str(item.get("price", "0"))
                price_krw = parse_price_krw(price_str)

                if not price_krw or not is_valid_card_listing(title, price_krw):
                    continue

                # 카드 번호로 먼저 매칭, 실패 시 이름으로 매칭
                card_number = extract_card_number(title)
                card = None
                if card_number:
                    card = match_card_by_number(card_number, all_cards)
                if not card:
                    card_name = extract_card_name(title)
                    if card_name:
                        card = match_card_by_name(card_name, all_cards)
                if not card:
                    continue

                if save_price_kr(card["id"], price_krw, "bunjang"):
                    saved += 1

            await asyncio.sleep(2)

    print(f"[번개장터] 완료 — {saved}건 저장")
    return saved
