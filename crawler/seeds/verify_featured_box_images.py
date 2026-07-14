"""featured 전체 — 박스 이미지 검증 (kr_sets · DB · pokemoncard 페이지)"""
from __future__ import annotations

import os
import re
import sys
import time

import httpx
from dotenv import load_dotenv
from supabase import create_client

from kr_sets import KR_SETS
from resolve_legacy_box_images import pick_box

PLACEHOLDER = "2016-06-20_00-44-39-61799-1466351079"
BAD_HOST = ("cdn.collectory.cc/cards/", "pokemontcg.io", "set-logo")


def is_pokemonkorea_box(url: str) -> bool:
    u = (url or "").lower()
    if not u:
        return False
    if any(b in u for b in BAD_HOST):
        return False
    if PLACEHOLDER in u:
        return False
    return "pokemonkorea.co.kr" in u


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

    issues = []
    ok = 0

    print(f"{'code':6} | {'page':>4} | stored | page | db | http")
    print("-" * 70)

    for s in KR_SETS:
        stored = s.box_image_kr or ""
        page_img = ""
        if s.pokemoncard_page:
            r = client.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}", timeout=15)
            r.encoding = "utf-8"
            page_img = pick_box(r.text)
            time.sleep(0.08)

        db_row = (
            sb.table("card_sets").select("image_url").eq("set_code", s.code).maybe_single().execute()
        )
        db_img = (db_row.data or {}).get("image_url") or ""

        probs = []
        if not is_pokemonkorea_box(stored):
            probs.append("stored_bad")
        if db_img and stored and db_img != stored:
            probs.append("db!=kr_sets")

        http_ok = True
        check_url = stored or page_img
        if check_url:
            try:
                hr = client.head(check_url)
                if hr.status_code >= 400:
                    http_ok = False
                    probs.append(f"http{hr.status_code}")
            except Exception:
                http_ok = False
                probs.append("http_err")

        # 페이지 이미지와 다르더라도 stored가 유효하면 OK (배너 vs 박스 차이)
        warn = ""
        if s.pokemoncard_page and page_img and stored and stored != page_img:
            sk = stored.split("/")[-1][:10]
            pk = page_img.split("/")[-1][:10]
            if sk != pk and sk not in page_img and pk not in stored:
                warn = " (page_diff)"

        flag = "OK" if not probs else ",".join(probs)
        if warn and not probs:
            flag = "OK" + warn
        if not probs:
            ok += 1
        else:
            issues.append((s.code, probs, stored[:60], page_img[:60], db_img[:60]))

        print(f"{s.code:6} | {s.pokemoncard_page:4} | {'Y' if is_pokemonkorea_box(stored) else 'N':6} | "
              f"{'Y' if page_img else 'N':4} | {'Y' if db_img else 'N':2} | {'Y' if http_ok else 'N':4} | {flag}")

    print(f"\ntotal={len(KR_SETS)} ok={ok} issues={len(issues)}")
    if issues:
        print("\n=== issues ===")
        for code, probs, st, pg, db in issues[:30]:
            print(f"{code}: {probs}")
            if st:
                print(f"  stored: {st}")
            if pg:
                print(f"  page:   {pg}")
        if len(issues) > 30:
            print(f"  ... +{len(issues)-30} more")


if __name__ == "__main__":
    main()
