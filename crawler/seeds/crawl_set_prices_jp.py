"""
일본판 raw 싱글 시세 — Collectory JP + 번개 일판 (KR와 동일 정책).

  python crawl_set_prices_jp.py --set MG6 --apply
  python crawl_set_prices_jp.py --set MG6 --apply --fallback   # 미등록만 유유테i 1장씩
"""
from __future__ import annotations

import os
import sys
import time

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_BY_CODE  # noqa: E402
from lib.collectory_jp import build_jp_card_id_map  # noqa: E402
from lib.collectory_public import preload_public_quotes_jp  # noqa: E402
from lib.jp_set_prices import (  # noqa: E402
    apply_jp_kr_guard,
    cards_needing_bunjang_jp,
    prefetch_bunjang_jp,
    resolve_jp_card_price,
    try_yuyutei_fallback,
)
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.yuyutei_prices import HEADERS as YUYU_HEADERS, YUYU_VERS  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

APPLY = "--apply" in sys.argv
QUIET = "--quiet" in sys.argv
FAST = "--thorough" not in sys.argv
YUYU_FALLBACK = "--fallback" in sys.argv


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


def _log(msg: str) -> None:
    if not QUIET:
        print(msg)


def _latest_kr_prices(card_ids: list[int]) -> dict[int, int]:
    if not card_ids:
        return {}
    out: dict[int, int] = {}
    batch = 200
    for i in range(0, len(card_ids), batch):
        chunk = card_ids[i : i + batch]
        res = (
            sb.table("prices_kr")
            .select("card_id,price_krw,fetched_at")
            .in_("card_id", chunk)
            .order("fetched_at", desc=True)
            .execute()
        )
        for row in res.data or []:
            cid = int(row["card_id"])
            if cid not in out:
                out[cid] = int(row.get("price_krw") or 0)
    return out


def crawl_one(
    set_code: str,
    rate: float,
    col_client: httpx.Client,
    yuyu_client: httpx.Client | None,
) -> tuple[int, int]:
    meta = KR_BY_CODE.get(set_code)
    if not meta:
        print(f"=== {set_code} — 세트 메타 없음, 스킵 ===")
        return 0, 0

    vers = YUYU_VERS.get(set_code, "")

    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print(f"=== {set_code} — DB 세트 없음 ===")
        return 0, 0
    set_name = row[0]["name_kr"]

    cards = (
        sb.table("cards")
        .select("id,card_number,name_jp,name_kr,rarity")
        .eq("set_id", row[0]["id"])
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    if not cards:
        print(f"=== {set_name}({set_code}) — 대상 카드 없음 ===")
        return 0, 0

    mode = "빠른" if FAST else "정밀"
    fb = " + 유유테i fallback" if YUYU_FALLBACK and vers else ""
    print(
        f"=== {set_name}({set_code}) 일본판 raw 싱글 시세 "
        f"[Collectory JP·번개{fb}, {mode}] ==="
    )
    print(f"대상: {len(cards)}장 (RR 이상)")

    id_map = build_jp_card_id_map(cards, col_client)
    print(f"Collectory JP card_id: {len(id_map)}/{len(cards)}장")

    quote_cache = {}
    if id_map:
        t0 = time.perf_counter()
        quote_cache = preload_public_quotes_jp(list(id_map.values()), col_client, workers=16)
        print(f"Collectory 거래내역: {len(quote_cache)}장 ({time.perf_counter() - t0:.1f}s)")

    bunjang_cache: dict[int, list[int]] = {}
    if FAST and cards:
        need = cards_needing_bunjang_jp(cards, id_map, quote_cache)
        if not id_map:
            need = list(cards)
        if need:
            t0 = time.perf_counter()
            bunjang_cache = prefetch_bunjang_jp(need, set_name, set_code, fast=True)
            print(
                f"번개 일판 보강: {len(need)}장 → {len(bunjang_cache)}건 "
                f"({time.perf_counter() - t0:.1f}s)"
            )

    rows: list[dict] = []
    ok = 0
    yuyu_fb_count = 0
    kr_prices = _latest_kr_prices([c["id"] for c in cards])
    for card in cards:
        median, low, n, source, price_jpy = resolve_jp_card_price(
            card,
            collectory_id=id_map.get(card["id"], ""),
            quote_cache=quote_cache,
            bunjang_cache=bunjang_cache if FAST else None,
            rate=rate,
            set_name_kr=set_name,
            set_code=set_code,
            fast=FAST,
        )
        if n == 0 and YUYU_FALLBACK and vers and yuyu_client is not None:
            median, low, n, source, price_jpy = try_yuyutei_fallback(
                card, vers=vers, rate=rate, client=yuyu_client
            )
            if n > 0:
                yuyu_fb_count += 1

        kr_price = kr_prices.get(card["id"], 0)
        if n > 0 and kr_price > 0 and median < kr_price:
            prev_src = source
            median, low, n, source, price_jpy = apply_jp_kr_guard(
                card,
                median,
                low,
                n,
                source,
                price_jpy,
                kr_price=kr_price,
                rate=rate,
                collectory_id=id_map.get(card["id"], ""),
                quote_cache=quote_cache,
                bunjang_cache=bunjang_cache if FAST else None,
                set_name_kr=set_name,
                set_code=set_code,
                fast=FAST,
                vers=vers,
                yuyu_client=yuyu_client if YUYU_FALLBACK else None,
            )
            if source != prev_src and source.startswith("listing:yuyutei"):
                yuyu_fb_count += 1

        if n > 0:
            tier = "체결" if source.startswith("sold") else "호가"
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp')} ({card.get('rarity')}) "
                f"=> ₩{median:,}"
                + (f" / ¥{price_jpy:,}" if price_jpy else "")
                + f" ({n}건, {tier}:{source})"
            )
            rows.append({
                "card_id": card["id"],
                "price_jpy": price_jpy or (round(median / rate) if rate else 0),
                "price_krw": median,
                "source": source,
            })
            ok += 1
        else:
            _log(
                f"  [{card.get('card_number')}] {card.get('name_jp')} ({card.get('rarity')}) => 미등록"
            )

    if YUYU_FALLBACK and yuyu_fb_count:
        print(f"유유테i fallback: {yuyu_fb_count}장")

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
        print("사용법: python crawl_set_prices_jp.py --set MG6 [--apply] [--fallback]")
        sys.exit(1)

    rate = get_exchange_rate()
    print(f"환율 JPY→KRW: {rate}")

    total_ok = 0
    total_cards = 0
    col_client = httpx.Client(
        timeout=30,
        headers={"User-Agent": YUYU_HEADERS["User-Agent"]},
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=24),
    )
    yuyu_client: httpx.Client | None = None
    if YUYU_FALLBACK:
        yuyu_client = httpx.Client(headers=YUYU_HEADERS, follow_redirects=True)

    try:
        for i, code in enumerate(targets):
            if i > 0:
                time.sleep(2)
            ok, n = crawl_one(code, rate, col_client, yuyu_client)
            total_ok += ok
            total_cards += n
            print()
    finally:
        col_client.close()
        if yuyu_client is not None:
            yuyu_client.close()

    print(f"합계: {total_ok}/{total_cards}장")


if __name__ == "__main__":
    main()
