"""
ExchangeRate-API를 통해 JPY→KRW 환율을 조회합니다.
"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


async def get_exchange_rate() -> float:
    """JPY→KRW 환율을 반환합니다. 실패 시 기본값 9.2를 반환합니다."""
    api_key = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
    if not api_key:
        print("[환율] API 키 없음 -- 기본값 9.5 사용")
        return 9.5

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://v6.exchangerate-api.com/v6/{api_key}/pair/JPY/KRW"
            )
            data = resp.json()
            rate = float(data["conversion_rate"])
            print(f"[환율] JPY→KRW = {rate}")
            return rate
    except Exception as e:
        print(f"[환율] 조회 실패: {e} -- 기본값 9.5 사용")
        return 9.5
