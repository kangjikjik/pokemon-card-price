"""featured 전체 — pokemoncard.co.kr 발매일·가격·이미지 검증"""
from __future__ import annotations

import json
import sys
import time

from kr_sets import KR_SETS
from verify_batch1_kr import scrape_page

OUT = __file__.replace("verify_featured_dates.py", "featured_dates_audit.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    mismatches = []
    no_date = []
    no_page = []

    print(f"{'code':6} | {'page':>4} | {'stored':12} | {'official':12} | {'pack':>6} | {'box':>7} | ok")
    print("-" * 95)

    for s in KR_SETS:
        if not s.pokemoncard_page:
            no_page.append(s.code)
            print(f"{s.code:6} | NO_PAGE")
            continue
        res = scrape_page(s.pokemoncard_page)
        time.sleep(0.15)
        official = res.get("released_at") or ""
        pack_ok = res.get("pack", 0) == s.msrp_pack_kr if res.get("pack") else True
        box_ok = res.get("box", 0) == s.msrp_box_kr if res.get("box") else True
        date_ok = official == s.released_at if official else False
        ok = date_ok and pack_ok and box_ok

        row = {
            "code": s.code,
            "name_kr": s.name_kr,
            "page": s.pokemoncard_page,
            "stored_date": s.released_at,
            "official_date": official,
            "stored_pack": s.msrp_pack_kr,
            "official_pack": res.get("pack", 0),
            "stored_box": s.msrp_box_kr,
            "official_box": res.get("box", 0),
            "title": res.get("title", ""),
            "box_image_kr": res.get("box_image_kr") or s.box_image_kr,
            "status": res.get("status", ""),
            "date_ok": date_ok,
            "pack_ok": pack_ok,
            "box_ok": box_ok,
        }
        rows.append(row)

        flag = "OK" if ok else "FIX"
        if not official:
            no_date.append(s.code)
            flag = "NO_DATE"
        elif not date_ok:
            mismatches.append(s.code)

        print(
            f"{s.code:6} | {s.pokemoncard_page:4} | {s.released_at:12} | "
            f"{official or '??':12} | {res.get('pack', 0):6} | {res.get('box', 0):7} | {flag}"
        )
        if not date_ok and official:
            print(f"       DATE MISMATCH: {s.released_at} -> {official}")
        if not pack_ok:
            print(f"       PACK: {s.msrp_pack_kr} -> {res.get('pack')}")
        if not box_ok:
            print(f"       BOX: {s.msrp_box_kr} -> {res.get('box')}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print()
    print(f"total={len(KR_SETS)} verified={len(rows)} date_mismatch={len(mismatches)} no_date={len(no_date)}")
    if mismatches:
        print("mismatches:", ", ".join(mismatches))


if __name__ == "__main__":
    main()
