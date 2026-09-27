from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.box_price_search import (
    build_box_search_queries,
    filter_bunjang_kr_box_quotes,
    filter_bunjang_jp_box_quotes,
    resolve_bunjang_box_price,
    jp_box_msrp_krw,
    jp_pack_msrp_krw,
)
from lib.price_history import save_daily_box_snapshots
from kr_sets import KR_BY_CODE
from utils.db import get_supabase
from crawl_box_prices import fetch_bunjang

sb = get_supabase()

# Lists of codes that were marked missing in last run (can be adjusted)
KR_MISSING = [
    "CEL","S2R","SM12a","SM12","SM11b","SM11a","SM9a","SM8","SM7",
    "SM6b","SM6a","SM6","SM5","SM4+",
]
JP_MISSING = [
    "SV2D","S9a","S7F","S7R","S7D","S5F","S5P","S5S","S3H","S3Z",
    "S2R","S2","S1H","SM12a","SM11a","SM9a","SM8","SM7","SM6a",
    "SM6","SM5+","SM5",
]

def process_code(set_code: str, region: str):
    meta = KR_BY_CODE.get(set_code)
    if not meta:
        print("unknown code", set_code)
        return
    # lookup set_id in DB
    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print("DB missing set", set_code)
        return
    set_id = row[0]["id"]
    set_name = row[0].get("name_kr") or meta.name_kr
    msrp = meta.msrp_box_kr or 30000
    pack_msrp = meta.msrp_pack_kr or 0
    sold_quotes = []
    listing_quotes = []
    seen = set()
    if region == "JP":
        msrp = jp_box_msrp_krw(set_code, 9.5)
        pack_msrp = jp_pack_msrp_krw(set_code, 9.5)
        queries = [q for q in build_box_search_queries(set_name, set_code)]
        filter_fn = filter_bunjang_jp_box_quotes
    else:
        queries = [q for q in build_box_search_queries(set_name, set_code)]
        filter_fn = filter_bunjang_kr_box_quotes

    used_queries = []
    for q in queries:
        items = fetch_bunjang(q)
        before = len(sold_quotes) + len(listing_quotes)
        # pass verifier=None to include items regardless of image
        sold, listings = filter_fn(items, set_name, set_code, msrp, pack_msrp)
        # merge unique pids
        for s in sold:
            if s.pid not in seen:
                seen.add(s.pid); sold_quotes.append(s)
        for l in listings:
            if l.pid not in seen:
                seen.add(l.pid); listing_quotes.append(l)
        if len(sold_quotes) + len(listing_quotes) > before:
            used_queries.append(q)
        time.sleep(0.2)

    price, count, tier = resolve_bunjang_box_price(sold_quotes, listing_quotes)
    source_prefix = "bunjang-jp" if region == "JP" else "bunjang"
    source = f"{source_prefix}:{tier}" if count > 0 else ""
    if count > 0 and used_queries and not source:
        source = f"{source_prefix}:{tier}:{used_queries[0][:30]}"

    # save snapshot
    deleted, inserted = save_daily_box_snapshots(
        sb,
        [set_id],
        region,
        [{
            "set_id": set_id,
            "region": region,
            "price_krw": price if price > 0 else 0,
            "source": source or (source_prefix if price > 0 else f"{source_prefix}:none"),
        }],
    )
    if price > 0:
        print(f"[{set_code}] -> {price:,}원 ({count}건) saved")
    else:
        print(f"[{set_code}] -> 미등록 (saved as none)")

def main():
    print("Processing KR missing")
    for code in KR_MISSING:
        process_code(code, "KR")
    print("Processing JP missing")
    for code in JP_MISSING:
        process_code(code, "JP")

if __name__ == "__main__":
    main()

