"""Verify SM5+ and BW4 manual RR+ supplements vs DB."""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from fill_oldest_rr_plus import MANUAL_SUPPLEMENTS, RR_PLUS, expected_catalog  # noqa: E402
from kr_sets import KR_BY_CODE  # noqa: E402

TARGETS = ["SM5+", "BW4"]  # BW4: featured 미포함 — DB 없으면 SKIP


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90)

    all_ok = True
    for code in TARGETS:
        if code not in KR_BY_CODE:
            print(f"=== {code} === SKIP (not in featured kr_sets)")
            print()
            continue
        s = KR_BY_CODE[code]
        expected = expected_catalog(code, s.collectory_id, client)
        manual_keys = {(m["card_number"], m["rarity"]) for m in MANUAL_SUPPLEMENTS.get(code, [])}

        set_id = sb.table("card_sets").select("id").eq("set_code", code).single().execute().data["id"]
        db_rr = (
            sb.table("cards")
            .select("id,card_number,rarity,name_kr,image_url")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        db_rr = [c for c in db_rr if (c.get("rarity") or "") in RR_PLUS]
        db_keys = {(c.get("card_number") or "", c.get("rarity") or "") for c in db_rr}

        missing = [k for k in expected if k not in db_keys]
        extra = [c for c in db_rr if (c.get("card_number") or "", c.get("rarity") or "") not in expected]
        manual_in_db = [k for k in manual_keys if k in db_keys]
        manual_missing = [k for k in manual_keys if k not in db_keys]

        print(f"=== {code} {s.name_kr} ===")
        print(f"  expected RR+: {len(expected)}")
        print(f"  db RR+: {len(db_rr)}")
        print(f"  missing: {len(missing)}")
        print(f"  extra: {len(extra)}")
        print(f"  manual supplements in DB: {len(manual_in_db)}/{len(manual_keys)}")
        if manual_missing:
            print("  manual MISSING:")
            for k in manual_missing:
                print(f"    - {k}")
        if missing[:10]:
            for k in missing[:10]:
                print(f"    missing {k}")
        if extra[:5]:
            for c in extra[:5]:
                print(f"    extra {c.get('card_number')} {c.get('rarity')} {c.get('name_kr')}")

        ok = not missing and len(manual_missing) == 0
        print(f"  RESULT: {'OK' if ok else 'FAIL'}")
        print()
        all_ok = all_ok and ok

    print("OVERALL:", "OK" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
