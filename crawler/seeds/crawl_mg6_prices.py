import os
import sys
import re
import json
import urllib.request
import urllib.parse
from time import sleep

# 상위 폴더의 모듈을 임포트하기 위해 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_tcgbox_prices(keyword: str) -> list[int]:
    """TCGbox에서 가격 목록 추출"""
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.tcgbox.co.kr/product/search.html?keyword={encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        # TCGbox 가격 패턴: 38,000원
        matches = re.findall(r'([0-9,]+)\s*원', html)
        prices = [int(m.replace(',', '')) for m in matches]
        # 너무 낮거나 높은 가격 제외 (예: 100원짜리 토큰 등)
        return [p for p in prices if 500 <= p <= 1000000]
    except Exception as e:
        print(f"  [TCGbox] 오류: {e}")
        return []

def get_bunjang_prices(keyword: str) -> list[int]:
    """번개장터에서 가격 목록 추출"""
    encoded = urllib.parse.quote(keyword)
    url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        res = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        data = json.loads(res)
        prices = [int(item['price']) for item in data.get('list', [])]
        return [p for p in prices if 500 <= p <= 1000000]
    except Exception as e:
        print(f"  [Bunjang] 오류: {e}")
        return []

def get_daangn_prices(keyword: str) -> list[int]:
    """당근마켓에서 가격 목록 추출"""
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.daangn.com/search/{encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        # 당근마켓 가격 패턴: <p class="article-price">38,000원</p>
        matches = re.findall(r'article-price[^>]*>([0-9,]+)(?:원|엔)?</p>', html)
        prices = [int(m.replace(',', '')) for m in matches]
        return [p for p in prices if 500 <= p <= 1000000]
    except Exception as e:
        print(f"  [Daangn] 오류: {e}")
        return []

def calculate_average(prices: list[int]) -> int:
    """이상치를 제외한 평균 계산"""
    if not prices:
        return 0
    if len(prices) < 3:
        return sum(prices) // len(prices)
    
    # 이상치 제거 (상위/하위 10% 제외, 최소 1개씩)
    sorted_prices = sorted(prices)
    trim_count = max(1, len(sorted_prices) // 10)
    trimmed = sorted_prices[trim_count:-trim_count]
    
    if not trimmed:
        trimmed = sorted_prices
        
    return sum(trimmed) // len(trimmed)

def main():
    print("=== 어비스아이(MG6) 시세 크롤링 시작 ===")
    
    # MG6 세트 조회
    s = sb.table('card_sets').select('id, name_kr').eq('set_code', 'MG6').single().execute()
    set_id = s.data['id']
    
    # 카드 목록 조회
    cards = sb.table('cards').select('id, card_number, name_kr, rarity').eq('set_id', set_id).execute()
    print(f"대상 카드 수: {len(cards.data)}장")
    
    success_count = 0
    
    for card in cards.data:
        name_kr = card['name_kr']
        rarity = card['rarity']
        print(f"\n[{card['card_number']}] {name_kr} ({rarity}) 검색 중...")
        
        # 검색 키워드 구성
        search_name = name_kr.replace(' ex', '').replace(' VSTAR', '').replace(' VMAX', '').replace(' V', '')
        keyword = f"포켓몬카드 {search_name}"
        
        tcg_prices = get_tcgbox_prices(search_name) # TCGbox는 이름만으로 검색
        bj_prices = get_bunjang_prices(keyword)
        dg_prices = get_daangn_prices(keyword)
        
        print(f"  - TCGbox: {len(tcg_prices)}건 발견")
        print(f"  - 번개장터: {len(bj_prices)}건 발견")
        print(f"  - 당근마켓: {len(dg_prices)}건 발견")
        
        all_prices = tcg_prices + bj_prices + dg_prices
        
        if all_prices:
            avg_price = calculate_average(all_prices)
            print(f"  => 평균 시세: {avg_price:,}원 (총 {len(all_prices)}건 기준)")
            
            # DB 저장
            sb.table('prices_kr').insert({
                'card_id': card['id'],
                'price_krw': avg_price,
                'source': 'average'
            }).execute()
            success_count += 1
        else:
            print("  => 시세 정보 없음")
            
        sleep(1) # 서버 부하 방지
        
    print(f"\n=== 크롤링 완료: 총 {success_count}장 시세 적용됨 ===")

if __name__ == "__main__":
    main()
