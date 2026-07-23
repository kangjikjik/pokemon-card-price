"""
대량 프로모 롤백 — PRM-* 전부 + CEL25PK/CEL30 (재시드 전).

  python purge_bulk_promo.py --apply

CEL·확장팩·featured 팩 내 P(SM12a 등)는 유지.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from promo_catalog import COMMEMORATIVE_ONLY_CODES  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()
APPLY = "--apply" in sys.argv


def delete_set(code: str) -> tuple[int, int]:
    row = sb.table("card_sets").select("id").eq("set_code", code).execute().data
    if not row:
        return 0, 0
    sid = row[0]["id"]
    cards = sb.table("cards").select("id").eq("set_id", sid).execute().data or []
    cids = [c["id"] for c in cards]
    price_n = 0
    if cids and APPLY:
        for i in range(0, len(cids), 100):
            chunk = cids[i : i + 100]
            sb.table("prices_kr").delete().in_("card_id", chunk).execute()
            price_n += len(chunk)
        sb.table("cards").delete().in_("id", cids).execute()
    if APPLY:
        sb.table("prices_box").delete().eq("set_id", sid).execute()
        sb.table("card_sets").delete().eq("id", sid).execute()
    return len(cids), price_n


def main() -> None:
    all_sets = sb.table("card_sets").select("set_code").execute().data or []
    prm = [s["set_code"] for s in all_sets if (s.get("set_code") or "").startswith("PRM-")]
    codes = sorted(set(prm + list(COMMEMORATIVE_ONLY_CODES)))
    print(f"{'[APPLY]' if APPLY else '[DRY]'} delete sets: {len(codes)}")
    total_c = total_p = 0
    for code in codes:
        c, p = delete_set(code)
        if c:
            print(f"  {code}: cards={c}")
        total_c += c
        total_p += p
    print(f"total cards={total_c}")


if __name__ == "__main__":
    main()
