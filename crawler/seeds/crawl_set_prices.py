"""
등급별 시세 수집 — 체결가 우선, 호가 최저가 fallback.

정책: 한글판 raw 싱글만.
  1) 거래 체결가 (카페/Break 등)
  2) 체결 없으면 호가 풀 최저가 (모든 등급)
  3) 둘 다 없으면 미등록
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.collectory_public import preload_public_quotes  # noqa: E402
from lib.price_history import save_daily_snapshots  # noqa: E402
from lib.price_resolve import PriceQuote  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from lib.price_search import (  # noqa: E402
    build_search_queries,
    calculate_average,
    calculate_conservative_price,
    calculate_min_price,
    calculate_median_price,
    calculate_trimmed_mean,
    filter_bunjang_listings,
    filter_prices_by_rarity_band,
    is_raw_kr_listing,
)
import httpx

from lib.collectory_prices import (  # noqa: E402
    CollectoryPriceIndex,
    HIGH_TIER_RARITIES,
    fetch_set_kr_prices,
    lookup_collectory_card_id,
    merge_collectory_primary,
    resolve_market_trades,
)
from kr_sets import KR_BY_CODE  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

APPLY = "--apply" in sys.argv
MISSING_ONLY = "--missing-only" in sys.argv
QUIET = "--quiet" in sys.argv
FAST = "--thorough" not in sys.argv  # 기본: 빠른 모드 (번개 병렬·DB 일괄·인증 API 생략)
BUNJANG_WORKERS = 8


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


ONLY_RARITY = get_arg("--rarity", "").upper() if "--rarity" in sys.argv else ""


def fetch_bunjang(keyword: str) -> list[dict]:
    encoded = urllib.parse.quote(keyword)
    url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded}&n=50"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        res = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        return json.loads(res).get("list", [])
    except Exception as e:
        print(f"    [번개장터] {e}")
        return []


def fetch_tcgbox(keyword: str, name_kr: str, rarity: str, card_number: str, set_code: str, set_name_kr: str) -> list[int]:
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.tcgbox.co.kr/product/search.html?keyword={encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        # 상품 블록 단위로 이름+가격 추출 시도
        blocks = re.split(r"<li[^>]*class=\"[^\"]*item[^\"]*\"", html)
        prices: list[int] = []
        r_upper = rarity.upper()
        for block in blocks:
            if name_kr[:4] not in block and name_kr.split()[0] not in block:
                continue
            title_m = re.search(r">([^<]{4,80})<", block)
            title = title_m.group(1) if title_m else block[:120]
            if not is_raw_kr_listing(title, name_kr, rarity, card_number, set_code, set_name_kr):
                continue
            if r_upper not in block.upper() and r_upper not in ("SR", "AR"):
                pass
            elif r_upper in ("SR", "SAR", "AR", "MUR"):
                if r_upper == "SR" and ("SAR" in block.upper() or "MUR" in block.upper()):
                    continue
                if r_upper == "AR" and any(x in block.upper() for x in ("SAR", "SR", "MUR")):
                    continue
            m = re.search(r"([0-9,]+)\s*원", block)
            if m:
                p = int(m.group(1).replace(",", ""))
                if 500 <= p <= 5_000_000:
                    prices.append(p)
        if not prices:
            matches = re.findall(r"([0-9,]+)\s*원", html)
            prices = [int(m.replace(",", "")) for m in matches if 500 <= int(m.replace(",", "")) <= 500_000]
        return prices
    except Exception as e:
        print(f"    [TCGbox] {e}")
        return []


def fetch_daangn(keyword: str, name_kr: str, rarity: str, card_number: str, set_code: str, set_name_kr: str) -> list[int]:
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.daangn.com/search/{encoded}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        titles = re.findall(r'article-title[^>]*>([^<]+)<', html)
        price_raw = re.findall(r"article-price[^>]*>([0-9,]+)", html)
        prices: list[int] = []
        for title, pr in zip(titles, price_raw):
            if not is_raw_kr_listing(title, name_kr, rarity, card_number, set_code, set_name_kr):
                continue
            p = int(pr.replace(",", ""))
            if 500 <= p <= 5_000_000:
                prices.append(p)
        return prices
    except Exception as e:
        print(f"    [당근] {e}")
        return []


def resolve_collectory_price(
    card: dict,
    col_prices: CollectoryPriceIndex | None,
    col_client: httpx.Client | None,
    *,
    quote_cache: dict[str, list[PriceQuote]] | None = None,
    use_auth_api: bool = True,
) -> tuple[list[int], list[int], list[str], list[str]]:
    """collectory 체결·호가 — 인증 API + 공개 카드 페이지(카페/Break)."""
    if col_prices is None:
        return [], [], [], []

    card_number = card.get("card_number") or ""
    name_kr = card["name_kr"] or ""
    rarity = card["rarity"] or ""
    cid = lookup_collectory_card_id(col_prices, card_number, name_kr, rarity)
    if not cid:
        return [], [], [], []

    preloaded = quote_cache.get(cid) if quote_cache else None
    return resolve_market_trades(
        cid, col_client, preloaded_quotes=preloaded, use_auth_api=use_auth_api,
    )


def pick_search_queries(
    set_name_kr: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
    *,
    fast: bool,
) -> list[str]:
    r_upper = rarity.upper()
    if fast:
        if r_upper in HIGH_TIER_RARITIES:
            return [
                f"포켓몬카드 {name_kr} {rarity}",
                f"포켓몬카드 {set_name_kr} {name_kr} {rarity}",
            ]
        return [
            f"포켓몬카드 {set_name_kr} {name_kr} {rarity}",
            f"포켓몬카드 {name_kr} {rarity} {set_name_kr}",
        ]
    queries = build_search_queries(set_name_kr, name_kr, rarity, card_number, set_code)
    if r_upper in HIGH_TIER_RARITIES:
        extra = [
            f"포켓몬카드 {name_kr} {rarity}",
            f"포켓몬카드 {set_name_kr} {name_kr} {rarity}",
        ]
        return extra + [q for q in queries if q not in extra]
    return queries


def _has_bunjang_listing(sources: list[str]) -> bool:
    return any(s in ("bunjang", "번개장터") or "bunjang" in (s or "").lower() for s in sources)


def _fetch_bunjang_prices(
    set_name_kr: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
    *,
    fast: bool,
) -> list[int]:
    queries = pick_search_queries(set_name_kr, name_kr, rarity, card_number, set_code, fast=fast)
    all_bj: list[int] = []
    for q in queries[:1 if fast else 3]:
        items = fetch_bunjang(q)
        all_bj.extend(filter_bunjang_listings(items, name_kr, rarity, card_number, set_code, set_name_kr))
        if all_bj:
            break
    if rarity.upper() in HIGH_TIER_RARITIES and not all_bj:
        for q in queries[:1]:
            items = fetch_bunjang(q)
            all_bj.extend(filter_bunjang_listings(
                items, name_kr, rarity, card_number, set_code, set_name_kr, relaxed=True,
            ))
            if all_bj:
                break
    return filter_prices_by_rarity_band(list(dict.fromkeys(all_bj)), rarity)


def _log(msg: str) -> None:
    if not QUIET:
        print(msg)


def _prefetch_bunjang(
    cards: list[dict],
    set_name_kr: str,
    set_code: str,
    *,
    fast: bool,
) -> dict[int, list[int]]:
    """번개 보강 대상 카드를 병렬 조회."""
    if not cards:
        return {}

    def _one(card: dict) -> tuple[int, list[int]]:
        return card["id"], _fetch_bunjang_prices(
            set_name_kr,
            card["name_kr"] or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            set_code,
            fast=fast,
        )

    out: dict[int, list[int]] = {}
    workers = min(BUNJANG_WORKERS, len(cards))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, c) for c in cards]
        for fut in as_completed(futures):
            cid, prices = fut.result()
            if prices:
                out[cid] = prices
    return out


def crawl_card(
    card: dict,
    set_name_kr: str,
    set_code: str,
    col_prices: CollectoryPriceIndex | None,
    col_client: httpx.Client | None,
    *,
    fast: bool = True,
    quote_cache: dict[str, list[PriceQuote]] | None = None,
    use_auth_api: bool = True,
    bunjang_cache: dict[int, list[int]] | None = None,
) -> tuple[int, int, int, str]:
    name_kr = card["name_kr"] or ""
    rarity = card["rarity"] or ""
    card_number = card.get("card_number") or ""

    sold_col: list[int] = []
    listing_col: list[int] = []
    sold_src: list[str] = []
    listing_src: list[str] = []
    if col_prices is not None:
        sold_col, listing_col, sold_src, listing_src = resolve_collectory_price(
            card, col_prices, col_client, quote_cache=quote_cache, use_auth_api=use_auth_api,
        )
    if sold_col:
        src_label = "+".join(dict.fromkeys(sold_src)) or "market"
        _log(f"    [체결] {src_label} {len(sold_col)}건 — {min(sold_col):,}원~")
    elif listing_col:
        src_label = "+".join(dict.fromkeys(listing_src)) or "listing"
        _log(f"    [호가] {src_label} {len(listing_col)}건 — 최저 {min(listing_col):,}원")

    merge_kwargs = dict(
        calculate_median_price=calculate_median_price,
        calculate_trimmed_mean=calculate_trimmed_mean,
        calculate_conservative_price=calculate_conservative_price,
        rarity=rarity,
        sold_prices=sold_col,
        listing_prices=list(listing_col),
        sold_sources=sold_src,
        listing_sources=list(listing_src),
    )

    if sold_col:
        return merge_collectory_primary(0, [], **merge_kwargs)

    extra_bj: list[int] = []
    if not _has_bunjang_listing(listing_src):
        if bunjang_cache is not None and card["id"] in bunjang_cache:
            extra_bj = bunjang_cache[card["id"]]
        elif bunjang_cache is None:
            extra_bj = _fetch_bunjang_prices(
                set_name_kr, name_kr, rarity, card_number, set_code, fast=fast,
            )
        if extra_bj:
            merge_kwargs["listing_prices"] = list(listing_col) + extra_bj
            merge_kwargs["listing_sources"] = list(listing_src) + ["bunjang"] * len(extra_bj)
            _log(f"    [번개 보강] {len(extra_bj)}건 — 최저 {min(extra_bj):,}원")

    return merge_collectory_primary(0, [], **merge_kwargs)


def verify_set_prices(set_code: str, set_id: str) -> list[str]:
    """시세 검증 — RR<AR 역전·MUR 최저가 오염 확인."""
    rows = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity,prices_kr(price_krw)")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    issues: list[str] = []
    by_base: dict[str, dict[str, int]] = {}

    for row in rows:
        rar = (row.get("rarity") or "").upper()
        prices = row.get("prices_kr") or []
        price = prices[0]["price_krw"] if prices else 0
        if price <= 0:
            continue
        if rar == "MUR" and price < 80_000:
            issues.append(f"MUR저가: {row['card_number']} {row['name_kr']} {price:,}원")
        base = (row.get("name_kr") or "").replace(" ex", "").strip()
        by_base.setdefault(base, {})[rar] = price

    for base, mp in sorted(by_base.items()):
        rr, ar = mp.get("RR", 0), mp.get("AR", 0)
        if rr > 0 and ar > 0 and rr >= ar:
            issues.append(f"RR>=AR: {base} RR {rr:,} / AR {ar:,}")

    print(f"\n=== {set_code} 시세 검증 ===")
    if issues:
        for msg in issues:
            print(f"  [WARN] {msg}")
    else:
        print("  OK — RR<AR, MUR 이상치 없음")
    return issues


def main() -> None:
    set_code = get_arg("--set", "MG6")
    s = sb.table("card_sets").select("id,set_code,name_kr").eq("set_code", set_code).single().execute()
    set_id = s.data["id"]
    set_name = s.data["name_kr"]

    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity")
        .eq("set_id", set_id)
        .order("card_number")
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]

    if ONLY_RARITY:
        cards = [c for c in cards if (c.get("rarity") or "").upper() == ONLY_RARITY]

    if MISSING_ONLY:
        priced = (
            sb.table("prices_kr")
            .select("card_id")
            .in_("card_id", [c["id"] for c in cards])
            .gt("price_krw", 0)
            .execute()
            .data
            or []
        )
        priced_ids = {r["card_id"] for r in priced}
        cards = [c for c in cards if c["id"] not in priced_ids]

    print(f"=== {set_name}({set_code}) 한글판 raw 싱글 시세 ===")
    suffix = ""
    if ONLY_RARITY:
        suffix += f" ({ONLY_RARITY}만)"
    if MISSING_ONLY:
        suffix += " (시세 없음만)"
    print(f"대상: {len(cards)}장" + suffix if suffix else f"대상: {len(cards)}장 (RR 이상)")
    mode = "빠른 모드" if FAST else "정밀 모드(--thorough)"
    print(f"모드: {mode} — 정밀: python crawl_set_prices.py --set {set_code} --thorough --apply")
    if FAST:
        print("  (빠른: 공개거래내역만·번개 병렬·DB 일괄저장)")
    if not APPLY:
        print("드라이런 — 반영: python crawl_set_prices.py --set", set_code, "--apply")
        cards = cards[:5]

    meta = KR_BY_CODE.get(set_code)
    col_prices: CollectoryPriceIndex | None = None
    col_client: httpx.Client | None = None
    quote_cache: dict[str, list[PriceQuote]] = {}
    use_auth_api = not FAST
    if meta and meta.collectory_id:
        col_client = httpx.Client(
            timeout=30,
            headers=HEADERS,
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=24),
        )
        col_prices = fetch_set_kr_prices(meta.collectory_id, client=col_client)
        print(f"collectory KR 시세 {len(col_prices.by_number)}건 로드 (1차 소스)")

        card_ids: list[str] = []
        for card in cards:
            cid = lookup_collectory_card_id(
                col_prices,
                card.get("card_number") or "",
                card["name_kr"] or "",
                card.get("rarity") or "",
            )
            if cid:
                card_ids.append(cid)
        if card_ids:
            import time as _time
            t0 = _time.perf_counter()
            quote_cache = preload_public_quotes(card_ids, col_client, workers=20)
            print(f"collectory 거래내역 {len(quote_cache)}장 프리로드 ({_time.perf_counter() - t0:.1f}s)")

    bunjang_cache: dict[int, list[int]] = {}
    if FAST and col_prices is not None:
        need_bj: list[dict] = []
        for card in cards:
            sold, listings, _, listing_src = resolve_collectory_price(
                card, col_prices, col_client, quote_cache=quote_cache, use_auth_api=False,
            )
            if not sold and not _has_bunjang_listing(listing_src):
                need_bj.append(card)
        if need_bj:
            import time as _time
            t0 = _time.perf_counter()
            bunjang_cache = _prefetch_bunjang(cards=need_bj, set_name_kr=set_name, set_code=set_code, fast=True)
            print(f"번개 보강 {len(need_bj)}장 병렬 조회 → {len(bunjang_cache)}건 ({_time.perf_counter() - t0:.1f}s)")

    ok = 0
    priced_rows: list[dict] = []
    try:
        for card in cards:
            _log(f"\n[{card['card_number']}] {card['name_kr']} ({card['rarity']})")
            median, low, n, source = crawl_card(
                card, set_name, set_code, col_prices, col_client,
                fast=FAST, quote_cache=quote_cache, use_auth_api=use_auth_api,
                bunjang_cache=bunjang_cache if FAST else None,
            )
            if n > 0:
                tier = "체결" if source.startswith("sold") else "호가최저"
                _log(f"  => {median:,}원 / 최저 {low:,}원 ({n}건, {tier}:{source})")
            else:
                _log("  => 미등록 (체결·호가 없음)")

            if APPLY:
                if median > 0:
                    priced_rows.append({
                        "card_id": card["id"],
                        "price_krw": median,
                        "source": source,
                    })
                    ok += 1
            if not FAST:
                sleep(0.8)
    finally:
        if col_client is not None:
            col_client.close()

    if APPLY and cards:
        all_ids = [c["id"] for c in cards]
        deleted, inserted = save_daily_snapshots(
            sb, "prices_kr", all_ids, priced_rows
        )
        unpriced = len(cards) - ok
        if not QUIET:
            print(
                f"  (일별 스냅샷: 오늘 교체 {deleted}건 → 저장 {inserted}건"
                + (f", 미등록 {unpriced}장 이력 유지)" if unpriced else ")")
            )

    if APPLY:
        print(f"\n완료: {ok}장 시세 저장 (과거 이력 유지)")
        verify_set_prices(set_code, set_id)
    else:
        print("\n(드라이런 샘플 5장만 조회)")


if __name__ == "__main__":
    main()
