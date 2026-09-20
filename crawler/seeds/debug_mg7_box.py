"""MG7 JP 박스 sold 필터 디버그."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.box_price_search import (
    build_jp_box_search_queries,
    filter_bunjang_jp_box_quotes,
    is_jp_box_listing,
)
from lib.box_image_verify import BoxImageVerifier
from kr_sets import KR_BY_CODE

# crawl_box_prices.fetch_bunjang inline
import json
import urllib.parse
import urllib.request

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://m.bunjang.co.kr/",
}


def fetch_bunjang(keyword: str, n: int = 80) -> list[dict]:
    encoded = urllib.parse.quote(keyword)
    url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded}&n={n}&order=date"
    req = urllib.request.Request(url, headers=HEADERS)
    res = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    return json.loads(res).get("list", [])


def main() -> None:
    code = "MG7"
    meta = KR_BY_CODE[code]
    msrp = 120000
    pack = 4000
    queries = build_jp_box_search_queries(meta.name_kr, code, "")
    print("queries sample:", queries[:5])

    seen: set[str] = set()
    all_items: list[dict] = []
    for q in queries[:10]:
        for it in fetch_bunjang(q):
            pid = str(it.get("pid", ""))
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            all_items.append(it)

    sold_raw = [it for it in all_items if str(it.get("status")) == "3"]
    print(f"items={len(all_items)} sold_raw={len(sold_raw)}")
    for it in sold_raw:
        title = it.get("name", "")
        if "슈링크" in title or "1box" in title.lower() or int(it.get("price") or 0) == 130000:
            price = int(it.get("price") or 0)
            ok = is_jp_box_listing(title, meta.name_kr, code, msrp, price, pack, allow_opened=True)
            print(f"  TARGET {'OK' if ok else 'NO'} {price:,} st={it.get('status')} {title[:80]}")
    for it in sold_raw[:8]:
        title = it.get("name", "")
        price = int(it.get("price") or 0)
        ok = is_jp_box_listing(title, meta.name_kr, code, msrp, price, pack, allow_opened=True)
        print(f"  {'OK' if ok else 'NO'} {price:,} {title[:75]}")

    with BoxImageVerifier(code, meta.box_image_kr or "") as v:
        sold_s, list_s = filter_bunjang_jp_box_quotes(
            all_items, meta.name_kr, code, msrp, pack, v
        )
        sold_r, list_r = filter_bunjang_jp_box_quotes(
            all_items, meta.name_kr, code, msrp, pack, None, allow_opened=True
        )
    print(f"strict+img sold={len(sold_s)} listing={len(list_s)}")
    print(f"relaxed sold={len(sold_r)} listing={len(list_r)}")


if __name__ == "__main__":
    main()
