"""MEGA(MG*) prices_jp — SNKRDUNK row 전부 삭제."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from utils.db import get_supabase

SETS = ["MG4", "MG4a", "MG5", "MG5a", "MG6", "MG7"]
APPLY = "--apply" in sys.argv


def main() -> None:
    sb = get_supabase()
    total = 0
    for code in SETS:
        row = sb.table("card_sets").select("id").eq("set_code", code).execute().data
        if not row:
            continue
        set_id = row[0]["id"]
        cards = sb.table("cards").select("id").eq("set_id", set_id).execute().data or []
        set_total = 0
        for c in cards:
            rows = (
                sb.table("prices_jp")
                .select("id,source")
                .eq("card_id", c["id"])
                .execute()
                .data
                or []
            )
            snk = [r for r in rows if "snkrdunk" in (r.get("source") or "")]
            set_total += len(snk)
            if APPLY:
                for r in snk:
                    sb.table("prices_jp").delete().eq("id", r["id"]).execute()
        if set_total:
            print(f"[{code}] SNK rows: {set_total}")
        total += set_total
    print(f"\n{'삭제' if APPLY else '드라이런'}: {total} rows")


if __name__ == "__main__":
    main()
