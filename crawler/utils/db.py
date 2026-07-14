"""
Supabase DB 저장 유틸리티 — 카드 매칭 + 시세 저장
"""
import os
import re
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            raise ValueError("SUPABASE_URL 또는 SUPABASE_SERVICE_KEY 환경 변수가 없습니다.")
        _client = create_client(url, key)
    return _client


def get_all_cards() -> list[dict]:
    """DB에서 전체 카드 목록을 가져옵니다."""
    try:
        supabase = get_supabase()
        result = supabase.table("cards").select(
            "id, card_number, name_kr, name_en, name_jp, rarity"
        ).execute()
        return result.data or []
    except Exception as e:
        print(f"[DB] 카드 목록 조회 실패: {e}")
        return []


def match_card_by_number(card_number: str, all_cards: list[dict]) -> dict | None:
    """카드 번호로 DB 카드를 매칭합니다. (예: '201/165')"""
    normalized = card_number.strip()
    for card in all_cards:
        if card.get("card_number", "").strip() == normalized:
            return card
    return None


def match_card_by_name(name: str, all_cards: list[dict]) -> dict | None:
    """카드 이름으로 DB 카드를 매칭합니다 (한국어/영어/일본어)."""
    name_clean = name.strip().lower()
    for card in all_cards:
        for field in ("name_kr", "name_en", "name_jp"):
            val = (card.get(field) or "").strip().lower()
            if val and (name_clean in val or val in name_clean):
                return card
    return None


def save_exchange_rate(jpy_to_krw: float) -> None:
    """환율을 DB에 저장합니다."""
    try:
        supabase = get_supabase()
        supabase.table("exchange_rates").insert({"jpy_to_krw": jpy_to_krw}).execute()
        print(f"[DB] 환율 저장: {jpy_to_krw}")
    except Exception as e:
        print(f"[DB] 환율 저장 실패: {e}")


def save_price_kr(card_id: int, price_krw: int, source: str) -> bool:
    """한국판 시세를 DB에 저장합니다."""
    try:
        supabase = get_supabase()
        supabase.table("prices_kr").insert({
            "card_id": card_id,
            "price_krw": price_krw,
            "source": source,
        }).execute()
        print(f"[DB] KR 저장: card_id={card_id}, ₩{price_krw:,}")
        return True
    except Exception as e:
        print(f"[DB] KR 저장 실패: {e}")
        return False


def save_price_jp(card_id: int, price_jpy: int, price_krw: int, source: str) -> bool:
    """일본판 시세를 DB에 저장합니다."""
    try:
        supabase = get_supabase()
        supabase.table("prices_jp").insert({
            "card_id": card_id,
            "price_jpy": price_jpy,
            "price_krw": price_krw,
            "source": source,
        }).execute()
        print(f"[DB] JP 저장: card_id={card_id}, ¥{price_jpy:,} → ₩{price_krw:,}")
        return True
    except Exception as e:
        print(f"[DB] JP 저장 실패: {e}")
        return False


def parse_price_krw(text: str) -> int | None:
    """
    가격 텍스트에서 정수 가격(원)을 추출합니다.
    예: '185,000원' → 185000 / '185000' → 185000
    """
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_price_jpy(text: str) -> int | None:
    """
    가격 텍스트에서 정수 가격(엔)을 추출합니다.
    예: '79,800 円' → 79800 / '79800' → 79800
    """
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None
