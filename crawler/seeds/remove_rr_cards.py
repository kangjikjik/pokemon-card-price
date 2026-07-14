"""
전 확장팩 RR 카드 및 연결 시세 삭제.

실행: python remove_rr_cards.py
      python remove_rr_cards.py --apply
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

APPLY = "--apply" in sys.argv
PAGE = 500


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    rr_ids: list[int] = []
    offset = 0
    while True:
        rows = (
            sb.table("cards")
            .select("id,set_id,card_number,name_kr,rarity")
            .eq("rarity", "RR")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
            or []
        )
        rr_ids.extend(r["id"] for r in rows)
        if len(rows) < PAGE:
            break
        offset += PAGE

    print(f"RR 카드 {len(rr_ids)}장 발견")
    if not rr_ids:
        return

    if not APPLY:
        sample = (
            sb.table("cards")
            .select("card_number,name_kr,rarity,card_sets(set_code)")
            .eq("rarity", "RR")
            .limit(10)
            .execute()
            .data
            or []
        )
        for c in sample:
            sc = (c.get("card_sets") or {}).get("set_code", "?")
            print(f"  예: {sc} {c.get('card_number')} {c.get('name_kr')}")
        print("\n드라이런 — 반영: python remove_rr_cards.py --apply")
        return

    deleted_prices = 0
    for i in range(0, len(rr_ids), 100):
        batch = rr_ids[i : i + 100]
        sb.table("prices_kr").delete().in_("card_id", batch).execute()
        sb.table("prices_jp").delete().in_("card_id", batch).execute()
        sb.table("cards").delete().in_("id", batch).execute()
        deleted_prices += len(batch)
        print(f"  삭제 {len(batch)}장...")

    print(f"\n완료: RR 카드 {len(rr_ids)}장 및 연결 시세 삭제")


if __name__ == "__main__":
    main()
