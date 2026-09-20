"""MG6 prices_jp 에서 SNKRDUNK 거래 row 전부 삭제."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from utils.db import get_supabase

APPLY = "--apply" in sys.argv


def main() -> None:
    sb = get_supabase()
    set_id = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute().data["id"]
    cards = sb.table("cards").select("id,card_number").eq("set_id", set_id).execute().data or []
    card_ids = [c["id"] for c in cards]

    total = 0
    for cid in card_ids:
        rows = (
            sb.table("prices_jp")
            .select("id,source")
            .eq("card_id", cid)
            .execute()
            .data
            or []
        )
        rows = [
            r
            for r in rows
            if "snkrdunk" in (r.get("source") or "")
        ]
        if rows:
            print(f"  card_id={cid}: {len(rows)} SNK rows")
            total += len(rows)
            if APPLY:
                for r in rows:
                    sb.table("prices_jp").delete().eq("id", r["id"]).execute()

    if APPLY:
        print(f"\n삭제 완료: {total} rows")
    else:
        print(f"\n드라이런: {total} rows — --apply 로 삭제")


if __name__ == "__main__":
    main()
