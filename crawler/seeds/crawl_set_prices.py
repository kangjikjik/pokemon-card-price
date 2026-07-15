"""
등급별 시세 수집 — collectory.cc 1차, 번개장터·TCGbox·당근 보조.

실행:
  python crawl_set_prices.py --set MG6
  python crawl_set_prices.py --set MG6 --apply
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from time import sleep

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

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
    fetch_collectory_market_price,
    fetch_set_kr_prices,
    lookup_collectory_card_id,
    lookup_collectory_price,
    merge_collectory_primary,
    search_kr_price,
)
from kr_sets import KR_BY_CODE  # noqa: E402

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

APPLY = "--apply" in sys.argv
MISSING_ONLY = "--missing-only" in sys.argv
FAST = "--thorough" not in sys.argv  # 기본: 빠른 모드 (번개 1~2회, 당근/TCGbox 생략)


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
) -> int:
    name_kr = card["name_kr"] or ""
    rarity = card["rarity"] or ""
    card_number = card.get("card_number") or ""

    col = 0
    if col_prices is not None:
        col = lookup_collectory_price(col_prices, card_number, name_kr, rarity)
    if col <= 0 and col_client is not None:
        col = search_kr_price(name_kr, card_number, rarity, client=col_client)
    return col


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


def crawl_card(
    card: dict,
    set_name_kr: str,
    set_code: str,
    col_prices: CollectoryPriceIndex | None,
    col_client: httpx.Client | None,
    *,
    fast: bool = True,
) -> tuple[int, int, int, str]:
    name_kr = card["name_kr"] or ""
    rarity = card["rarity"] or ""
    card_number = card.get("card_number") or ""

    collectory = resolve_collectory_price(card, col_prices, col_client)
    if collectory > 0:
        print(f"    [collectory 최저] {collectory:,}원")

    col_market = 0
    if col_prices is not None and col_client is not None:
        cid = lookup_collectory_card_id(col_prices, card_number, name_kr, rarity)
        if cid:
            col_market = fetch_collectory_market_price(cid, col_client)
            if col_market > 0:
                print(f"    [collectory 시세] {col_market:,}원")

    r_upper = rarity.upper()
    queries = pick_search_queries(set_name_kr, name_kr, rarity, card_number, set_code, fast=fast)

    # collectory 거래 시세 확보 시 번개 생략 (스크린샷 현재 시세와 동일)
    if fast and col_market > 0:
        return merge_collectory_primary(
            collectory,
            [],
            calculate_median_price=calculate_median_price,
            calculate_trimmed_mean=calculate_trimmed_mean,
            calculate_conservative_price=calculate_conservative_price,
            rarity=rarity,
            collectory_market=col_market,
        )

    all_bj: list[int] = []
    all_tcg: list[int] = []
    all_dg: list[int] = []
    max_queries = 2 if fast else 8
    min_bj = 3 if fast else 5

    for q in queries[:max_queries]:
        items = fetch_bunjang(q)
        batch = filter_bunjang_listings(items, name_kr, rarity, card_number, set_code, set_name_kr)
        all_bj.extend(batch)
        if not fast:
            all_tcg.extend(fetch_tcgbox(q, name_kr, rarity, card_number, set_code, set_name_kr))
            all_dg.extend(fetch_daangn(q, name_kr, rarity, card_number, set_code, set_name_kr))
        if len(all_bj) >= min_bj:
            break
        if fast:
            sleep(0.12)
        else:
            sleep(0.4)

    if r_upper in HIGH_TIER_RARITIES and len(all_bj) < 3:
        for q in queries[:2]:
            items = fetch_bunjang(q)
            batch = filter_bunjang_listings(
                items, name_kr, rarity, card_number, set_code, set_name_kr, relaxed=True,
            )
            all_bj.extend(batch)
            if fast:
                sleep(0.12)
            else:
                sleep(0.4)

    market = list(dict.fromkeys(all_bj + all_tcg + all_dg))
    market = filter_prices_by_rarity_band(market, rarity)

    return merge_collectory_primary(
        collectory,
        market,
        calculate_median_price=calculate_median_price,
        calculate_trimmed_mean=calculate_trimmed_mean,
        calculate_conservative_price=calculate_conservative_price,
        rarity=rarity,
        collectory_market=col_market,
    )


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

    print(f"=== {set_name}({set_code}) 미등급 한글판 시세 ===")
    suffix = ""
    if ONLY_RARITY:
        suffix += f" ({ONLY_RARITY}만)"
    if MISSING_ONLY:
        suffix += " (시세 없음만)"
    print(f"대상: {len(cards)}장" + suffix if suffix else f"대상: {len(cards)}장 (RR 이상)")
    mode = "빠른 모드" if FAST else "정밀 모드(--thorough)"
    print(f"모드: {mode} — 정밀: python crawl_set_prices.py --set {set_code} --thorough --apply")
    if not APPLY:
        print("드라이런 — 반영: python crawl_set_prices.py --set", set_code, "--apply")
        cards = cards[:5]

    meta = KR_BY_CODE.get(set_code)
    col_prices: CollectoryPriceIndex | None = None
    col_client: httpx.Client | None = None
    if meta and meta.collectory_id:
        col_client = httpx.Client(timeout=60, headers=HEADERS)
        col_prices = fetch_set_kr_prices(meta.collectory_id, client=col_client)
        print(f"collectory KR 시세 {len(col_prices.by_number)}건 로드 (1차 소스)")

    ok = 0
    try:
        for card in cards:
            print(f"\n[{card['card_number']}] {card['name_kr']} ({card['rarity']})")
            median, low, n, source = crawl_card(
                card, set_name, set_code, col_prices, col_client, fast=FAST,
            )
            if n > 0:
                print(f"  => 중앙값 {median:,}원 / 최저 {low:,}원 ({n}건, {source})")
            else:
                print(f"  => 매물 없음")

            if APPLY:
                sb.table("prices_kr").delete().eq("card_id", card["id"]).execute()
                if median > 0:
                    sb.table("prices_kr").insert({
                        "card_id": card["id"],
                        "price_krw": median,
                        "source": source,
                    }).execute()
                    ok += 1
                else:
                    print("  (기존 시세 삭제)")
            if not FAST:
                sleep(0.8)
    finally:
        if col_client is not None:
            col_client.close()

    if APPLY:
        print(f"\n완료: {ok}장 시세 저장")
        verify_set_prices(set_code, set_id)
    else:
        print("\n(드라이런 샘플 5장만 조회)")


if __name__ == "__main__":
    main()
