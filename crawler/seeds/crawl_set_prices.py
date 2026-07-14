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

from lib.price_search import (  # noqa: E402
    build_search_queries,
    calculate_average,
    calculate_min_price,
    calculate_median_price,
    filter_bunjang_listings,
    filter_prices_by_rarity_band,
    is_raw_kr_listing,
)
import httpx

from lib.collectory_prices import (  # noqa: E402
    CollectoryPriceIndex,
    fetch_set_kr_prices,
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
SKIP_RR = {"RR"}


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


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


def crawl_card(
    card: dict,
    set_name_kr: str,
    set_code: str,
    col_prices: CollectoryPriceIndex | None,
    col_client: httpx.Client | None,
) -> tuple[int, int, int, str]:
    name_kr = card["name_kr"] or ""
    rarity = card["rarity"] or ""
    card_number = card.get("card_number") or ""

    collectory = resolve_collectory_price(card, col_prices, col_client)
    if collectory > 0:
        print(f"    [collectory] {collectory:,}원")

    queries = build_search_queries(set_name_kr, name_kr, rarity, card_number, set_code)

    all_bj: list[int] = []
    all_tcg: list[int] = []
    all_dg: list[int] = []

    for q in queries[:6]:
        items = fetch_bunjang(q)
        batch = filter_bunjang_listings(items, name_kr, rarity, card_number, set_code, set_name_kr)
        all_bj.extend(batch)
        all_tcg.extend(fetch_tcgbox(q, name_kr, rarity, card_number, set_code, set_name_kr))
        all_dg.extend(fetch_daangn(q, name_kr, rarity, card_number, set_code, set_name_kr))
        if len(all_bj) >= 5:
            break
        sleep(0.4)

    market = list(dict.fromkeys(all_bj + all_tcg + all_dg))
    market = filter_prices_by_rarity_band(market, rarity)

    return merge_collectory_primary(
        collectory,
        market,
        calculate_median_price=calculate_median_price,
    )


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
    cards = [c for c in cards if c.get("rarity") not in SKIP_RR]

    print(f"=== {set_name}({set_code}) 미등급 한글판 시세 ===")
    print(f"대상: {len(cards)}장 (RR 제외)")
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
            median, low, n, source = crawl_card(card, set_name, set_code, col_prices, col_client)
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
            sleep(0.8)
    finally:
        if col_client is not None:
            col_client.close()

    if APPLY:
        print(f"\n완료: {ok}장 시세 저장")
    else:
        print("\n(드라이런 샘플 5장만 조회)")


if __name__ == "__main__":
    main()
