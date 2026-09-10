"""
JP 확장팩 카드 시세 — 번개장터 + SNKRDUNK.

정책 (crawler/PRICING.md):
  1) 번개장터·SNKRDUNK 거래완료 → 합산 평균 (sold:bunjang+snkrdunk)
  2) 체결 없으면 번개장터 판매중(status=0) 최저가
  3) 단품 싱글만 (일본판 표기, qty=1 / SNKRDUNK RAW)

  python crawl_set_prices_jp.py --set MG6
  python crawl_set_prices_jp.py --set MG6 --apply
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.bunjang_card_price import prefetch_bunjang_jp  # noqa: E402
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.price_search import filter_prices_by_rarity_band  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.snkrdunk_card_price import merge_jp_card_price, prefetch_snkrdunk_sold_jp  # noqa: E402
from kr_sets import KR_BY_CODE, KR_SETS  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv
WORKERS = 16


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


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


def _log(msg: str) -> None:
    if not QUIET:
        print(msg)


def resolve_set_code(raw: str) -> str:
    key = raw.strip().upper()
    for code in KR_BY_CODE:
        if code.upper() == key:
            return code
    return raw.strip().upper()


def crawl_one(set_code: str, rate: float, client: httpx.Client) -> tuple[int, int]:
    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print(f"=== {set_code} — DB 세트 없음 ===")
        return 0, 0
    set_name = row[0]["name_kr"]
    set_id = row[0]["id"]

    cards = (
        sb.table("cards")
        .select("id,card_number,name_jp,name_kr,rarity")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    if not cards:
        print(f"=== {set_name}({set_code}) — 대상 카드 없음 ===")
        return 0, 0

    print(f"=== {set_name}({set_code}) JP 시세 [번개장터 + SNKRDUNK] ===")
    print(f"대상: {len(cards)}장")

    bunjang_prefetch = prefetch_bunjang_jp(cards, set_name, set_code, workers=WORKERS)
    print(f"번개 조회 완료: {len(bunjang_prefetch)}/{len(cards)}장 매칭")

    print(f"SNKRDUNK 체결 조회 중 (Collectory 공개 SNKRDUNK 행)...")
    snk_prefetch = prefetch_snkrdunk_sold_jp(cards, client, workers=WORKERS)
    print(f"SNKRDUNK 조회 완료: {len(snk_prefetch)}/{len(cards)}장 매칭")

    rows: list[dict] = []
    ok = 0

    for card in cards:
        cid = card["id"]
        if cid in bunjang_prefetch:
            b_sold, b_listing = bunjang_prefetch[cid]
        else:
            b_sold, b_listing = [], []
        s_sold = snk_prefetch.get(cid, [])

        rarity = card.get("rarity") or ""
        b_sold = filter_prices_by_rarity_band(b_sold, rarity)
        b_listing = filter_prices_by_rarity_band(b_listing, rarity)
        s_sold = filter_prices_by_rarity_band(s_sold, rarity)

        price_krw, count, source = merge_jp_card_price(b_sold, b_listing, s_sold)

        if count > 0:
            price_jpy = round(price_krw / rate) if rate else 0
            if source.startswith("sold"):
                tier = "거래완료"
            else:
                tier = "호가최저"
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')}"
                f" ({rarity}) => ₩{price_krw:,} / ¥{price_jpy:,} ({count}건, {tier}, {source})"
            )
            rows.append({
                "card_id": card["id"],
                "price_jpy": price_jpy,
                "price_krw": price_krw,
                "source": source,
            })
            ok += 1
        else:
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp') or card.get('name_kr')}"
                f" ({rarity}) => 미등록"
            )

    if APPLY:
        ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(sb, "prices_jp", ids, rows)
        print(f"완료: {ok}/{len(cards)}장 저장 (교체 {deleted}→{inserted})")
    else:
        print(f"드라이런: {ok}/{len(cards)}장 매칭")

    return ok, len(cards)


def main() -> None:
    targets: list[str] = []
    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        targets = [resolve_set_code(s) for s in sys.argv[idx + 1:] if not s.startswith("-")]
    elif "--all" in sys.argv:
        targets = [s.code for s in KR_SETS]
    else:
        print("사용법:")
        print("  python crawl_set_prices_jp.py --set MG6 [--apply]")
        print("  python crawl_set_prices_jp.py --all --apply")
        sys.exit(1)

    rate = get_exchange_rate()
    print(f"환율 JPY→KRW: {rate}")

    total_ok = total_cards = 0
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=20.0), headers={"User-Agent": "Mozilla/5.0"}) as client:
        for i, code in enumerate(targets):
            if i > 0:
                print()
            ok, n = crawl_one(code, rate, client)
            total_ok += ok
            total_cards += n

    if len(targets) > 1:
        print(f"\n합계: {total_ok}/{total_cards}장")


if __name__ == "__main__":
    main()
