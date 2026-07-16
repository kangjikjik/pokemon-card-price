"""
일본판 raw 싱글 시세 — 유유테이 판매가(최저) 기준.

  python crawl_set_prices_jp.py --set MG6 --apply
  python crawl_set_prices_jp.py --set MG6 MG5a MG5 --apply
"""
from __future__ import annotations

import os
import sys
import time

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_BY_CODE  # noqa: E402
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.yuyutei_prices import (  # noqa: E402
    HEADERS,
    YUYU_VERS,
    card_numbers_match,
    fetch_set_listings,
)

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv


def get_exchange_rate() -> float:
    key = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
    if key:
        try:
            r = httpx.get(
                f"https://v6.exchangerate-api.com/v6/{key}/pair/JPY/KRW",
                timeout=10,
            )
            return float(r.json()["conversion_rate"])
        except Exception:
            pass
    return 9.5


def resolve_set_code(raw: str) -> str:
    key = raw.strip().upper()
    for code in KR_BY_CODE:
        if code.upper() == key:
            return code
    return raw.strip().upper()


def get_target_sets() -> list[str]:
    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        return [resolve_set_code(s) for s in sys.argv[idx + 1 :] if not s.startswith("-")]
    return []


def crawl_one(set_code: str, rate: float, client: httpx.Client) -> tuple[int, int]:
    meta = KR_BY_CODE.get(set_code)
    vers = YUYU_VERS.get(set_code)
    if not meta or not vers:
        print(f"=== {set_code} — 유유테이 vers 미등록, 스킵 ===")
        return 0, 0

    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print(f"=== {set_code} — DB 세트 없음 ===")
        return 0, 0
    set_id = row[0]["id"]
    set_name = row[0]["name_kr"]

    cards = (
        sb.table("cards")
        .select("id,card_number,name_jp,rarity")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    if not cards:
        print(f"=== {set_name}({set_code}) — 대상 카드 없음 ===")
        return 0, 0

    print(f"=== {set_name}({set_code}) 일본판 raw 싱글 시세 [유유테이 {vers}] ===")
    print(f"대상: {len(cards)}장 (RR 이상)")

    listings = fetch_set_listings(vers, client)
    if not listings:
        raise RuntimeError(
            f"{set_code}: 유유테이 429 차단 또는 데이터 없음 — 자동 배치를 중단합니다"
        )
    print(f"유유테이 수집: {len(listings)}건 (카드번호 기준)")

    rows: list[dict] = []
    ok = 0
    for card in cards:
        db_num = card.get("card_number") or ""
        hit = None
        for _key, listing in listings.items():
            if card_numbers_match(db_num, listing.card_number):
                hit = listing
                break
        if hit:
            price_krw = round(hit.price_jpy * rate)
            if not QUIET:
                print(
                    f"  [{db_num or hit.card_number}] {card.get('name_jp') or hit.name_jp} "
                    f"({card.get('rarity')}) => ¥{hit.price_jpy:,} / ₩{price_krw:,}"
                )
            rows.append({
                "card_id": card["id"],
                "price_jpy": hit.price_jpy,
                "price_krw": price_krw,
                "source": "yuyutei",
            })
            ok += 1
        elif not QUIET:
            print(f"  [{db_num}] {card.get('name_jp')} ({card.get('rarity')}) => 미등록")

    if APPLY:
        ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_jp", ids, rows)
        print(
            f"완료: {ok}/{len(cards)}장 시세 저장 "
            f"(오늘 교체 {deleted}→{inserted}, 과거 이력 유지)"
        )
    else:
        print(f"드라이런: {ok}/{len(cards)}장 매칭 (반영: --apply)")

    return ok, len(cards)


def main() -> None:
    targets = get_target_sets()
    if not targets:
        print("사용법: python crawl_set_prices_jp.py --set MG6 [--apply]")
        sys.exit(1)

    rate = get_exchange_rate()
    print(f"환율 JPY→KRW: {rate}")

    total_ok = 0
    total_cards = 0
    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for i, code in enumerate(targets):
            if i > 0:
                time.sleep(5)
            ok, n = crawl_one(code, rate, client)
            total_ok += ok
            total_cards += n
            print()

    print(f"합계: {total_ok}/{total_cards}장")


if __name__ == "__main__":
    main()
