"""

박스 시세 수집 — 번개장터 (한국판 / 일본판 미개봉).



정책:

  - 제목·가격·묶음 필터 + 기준 박스 이미지 유사도 검증

  - 최근 거래완료(status=3) 우선 (90일 이내)

  - 거래완료가 없거나 너무 오래됐으면 판매중(status=0) 호가

  - 1건이면 그 가격, 여러 건이면 중앙값



  python crawl_box_prices.py --set MG6 --apply

  python crawl_box_prices.py --set MG6 --region JP --apply

  python crawl_box_prices.py --apply --all --region JP

"""

from __future__ import annotations



import json

import os

import sys

import urllib.parse

import urllib.request

from time import sleep



from dotenv import load_dotenv



sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

sys.stdout.reconfigure(encoding="utf-8")



from lib.box_image_verify import BoxImageVerifier  # noqa: E402

from lib.box_price_search import (  # noqa: E402

    VerifiedBoxQuote,

    build_box_search_queries,

    build_jp_box_search_queries,

    filter_bunjang_jp_box_quotes,

    filter_bunjang_kr_box_quotes,

    jp_box_msrp_krw,

    jp_pack_msrp_krw,

    resolve_bunjang_box_price,

)

from lib.price_history import save_daily_box_snapshots  # noqa: E402

from kr_sets import KR_BY_CODE, KR_SETS  # noqa: E402

from utils.db import get_supabase  # noqa: E402



load_dotenv()

sb = get_supabase()



HEADERS = {

    "User-Agent": (

        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    ),

    "Referer": "https://m.bunjang.co.kr/",

}



APPLY = "--apply" in sys.argv

QUIET = "--quiet" in sys.argv





def get_arg(flag: str, default: str = "") -> str:

    if flag in sys.argv:

        idx = sys.argv.index(flag)

        if idx + 1 < len(sys.argv):

            return sys.argv[idx + 1]

    return default





def get_region() -> str:

    r = get_arg("--region", "KR").upper()

    return "JP" if r == "JP" else "KR"





def resolve_set_code(code: str) -> str:
    if not code:
        return code
    if code in KR_BY_CODE:
        return code
    for key in KR_BY_CODE:
        if key.upper() == code.upper():
            return key
    return code


def _log(msg: str) -> None:

    if not QUIET:

        print(msg)





def fetch_bunjang(keyword: str) -> list[dict]:

    encoded = urllib.parse.quote(keyword)

    url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded}&n=100"

    try:

        req = urllib.request.Request(url, headers=HEADERS)

        res = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")

        return json.loads(res).get("list", [])

    except Exception as e:

        print(f"    [번개장터] {e}")

        return []





def _merge_quotes(

    seen_pids: set[str],

    items: list[dict],

    sold_out: list[VerifiedBoxQuote],

    listing_out: list[VerifiedBoxQuote],

    filter_fn,

    set_name: str,

    set_code: str,

    msrp: int,

    pack_msrp: int,

    verifier: BoxImageVerifier,

    *,
    sold_trades_out: list[VerifiedBoxQuote] | None = None,
    seen_trade_pids: set[str] | None = None,

) -> None:

    for item in items:

        pid = str(item.get("pid", "") or "")

        if pid and pid in seen_pids:

            continue

        sold, listings = filter_fn(

            [item], set_name, set_code, msrp, pack_msrp, verifier

        )

        if not sold and not listings:

            continue

        if pid:

            seen_pids.add(pid)

        sold_out.extend(sold)

        listing_out.extend(listings)

        # 거래내역용 — 이미지 검증·개봉 필터 완화, 미개봉 표기 없어도 포함
        if sold_trades_out is not None:
            trade_sold, _ = filter_fn(
                [item], set_name, set_code, msrp, pack_msrp, None,
                allow_opened=True,
            )
            trade_pids = seen_trade_pids if seen_trade_pids is not None else seen_pids
            for q in trade_sold:
                tp = q.pid or ""
                if tp and tp in trade_pids:
                    continue
                if tp:
                    trade_pids.add(tp)
                sold_trades_out.append(q)





def crawl_set_box(set_code: str, region: str, rate: float = 9.5) -> tuple[int, int, str]:

    """Returns (price, count, source)."""

    meta = KR_BY_CODE.get(set_code)

    if not meta:

        print(f"  알 수 없는 세트: {set_code}")

        return 0, 0, ""



    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data

    if not row:

        print(f"  DB에 세트 없음: {set_code}")

        return 0, 0, ""



    set_id = row[0]["id"]

    set_name = row[0].get("name_kr") or meta.name_kr

    jp_name = ""

    ref_url = meta.box_image_kr or ""



    if region == "JP":

        from lib.box_price_search import _load_jp_msrp



        _, jp_names = _load_jp_msrp()

        jp_name = jp_names.get(set_code, "")

        msrp = jp_box_msrp_krw(set_code, rate)

        pack_msrp = jp_pack_msrp_krw(set_code, rate)

        queries = build_jp_box_search_queries(set_name, set_code, jp_name)

        filter_fn = filter_bunjang_jp_box_quotes

        source_prefix = "bunjang-jp"

    else:

        msrp = meta.msrp_box_kr or 30000

        pack_msrp = meta.msrp_pack_kr or 0

        queries = build_box_search_queries(set_name, set_code)

        filter_fn = filter_bunjang_kr_box_quotes

        source_prefix = "bunjang"



    sold_quotes: list[VerifiedBoxQuote] = []

    listing_quotes: list[VerifiedBoxQuote] = []

    sold_trades: list[VerifiedBoxQuote] = []

    seen_pids: set[str] = set()

    seen_trade_pids: set[str] = set()

    used_queries: list[str] = []



    with BoxImageVerifier(set_code, ref_url) as verifier:

        if not verifier.has_reference():

            _log(f"  [경고] 기준 박스 이미지 없음 — {set_code}")



        for q in queries:

            items = fetch_bunjang(q)

            before = len(sold_quotes) + len(listing_quotes)

            _merge_quotes(

                seen_pids,

                items,

                sold_quotes,

                listing_quotes,

                filter_fn,

                set_name,

                set_code,

                msrp,

                pack_msrp,

                verifier,

                sold_trades_out=sold_trades,

                seen_trade_pids=seen_trade_pids,

            )

            if len(sold_quotes) + len(listing_quotes) > before:

                used_queries.append(q)

            sleep(0.3)



    effective_sold = sold_trades if sold_trades else sold_quotes
    price, count, tier = resolve_bunjang_box_price(effective_sold, listing_quotes)

    source = f"{source_prefix}:{tier}" if count > 0 else ""

    if count > 0 and used_queries and not source:

        source = f"{source_prefix}:{tier}:{used_queries[0][:30]}"



    if APPLY:

        # 개별 거래 rows — 거래내역용(완화 필터) 우선, 없으면 시세용 strict
        trade_source = sorted(
            sold_trades if sold_trades else sold_quotes,
            key=lambda q: q.updated_at,
            reverse=True,
        )
        rows: list[dict] = []
        if price > 0:
            # 카드와 동일하게 대표 시세 요약 행과 개별 거래 행을 함께 저장한다.
            # 요약 행은 시세 추이, 개별 행은 링크·실제 거래일 표시에 사용한다.
            rows.append({
                "set_id": set_id,
                "region": region,
                "price_krw": price,
                "source": source,
            })
        for q in trade_source[:10]:
            if not q.pid:
                continue
            src = f"{source_prefix}:sold:{q.pid}:{q.updated_at}"
            rows.append({"set_id": set_id, "region": region, "price_krw": q.price, "source": src})
        # sold가 없을 때만 listing 저장 (URL 필수)
        if not rows:
            for q in listing_quotes[:10]:
                if not q.pid:
                    continue
                src = f"{source_prefix}:listing:{q.pid}:{q.updated_at}"
                rows.append({"set_id": set_id, "region": region, "price_krw": q.price, "source": src})
        # 아무것도 없으면 미등록 row
        if not rows:
            rows.append({"set_id": set_id, "region": region, "price_krw": 0, "source": f"{source_prefix}:none"})

        deleted, inserted = save_daily_box_snapshots(

            sb,

            [set_id],

            region,

            rows,

        )

        tier_label = "거래완료" if tier == "sold" else "호가"

        if price > 0:

            _log(f"  (일별 스냅샷: {tier_label} {deleted}건 교체 → 저장 {inserted}건)")

        else:

            _log(f"  (일별 스냅샷: 시세 없음 → 오늘 {deleted}건 교체, 미등록 저장 {inserted}건)")



    return price, count, source





def main() -> None:

    region = get_region()

    single = resolve_set_code(get_arg("--set", ""))

    run_all = "--all" in sys.argv



    if single:

        targets = [single]

    elif run_all:

        targets = [s.code for s in KR_SETS if (s.msrp_box_kr > 0 if region == "KR" else True)]

    else:

        print("사용법:")

        print("  python crawl_box_prices.py --set MG6 --apply")

        print("  python crawl_box_prices.py --set MG6 --region JP --apply")

        print("  python crawl_box_prices.py --apply --all --region JP")

        return



    label = "일본판" if region == "JP" else "한국판"

    print(f"=== {label} 박스 시세 ({len(targets)}팩) — 이미지검증 + 거래완료/호가 ===")

    if not APPLY:

        print("드라이런 — 반영: --apply 추가")



    ok = 0

    for code in targets:

        meta = KR_BY_CODE.get(code)

        name = meta.name_kr if meta else code

        print(f"\n[{code}] {name}")

        price, count, source = crawl_set_box(code, region)

        if count > 0:

            tier = "거래완료" if ":sold" in source else "호가"

            print(f"  => {price:,}원 ({count}건 {tier}, {source})")

            ok += 1

        else:

            print("  => 미등록 (검증 통과 매물 없음)")



    print(f"\n완료: {ok}/{len(targets)}팩 시세 {'저장' if APPLY else '조회'}")





if __name__ == "__main__":

    main()

