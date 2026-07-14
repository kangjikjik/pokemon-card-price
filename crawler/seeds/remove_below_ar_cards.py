"""
AR 미만 등급 카드 및 연결 시세 삭제 (S·CHR·RRR·잘못된 등급 등).

실행:
  python remove_below_ar_cards.py --set SV4a
  python remove_below_ar_cards.py --set SV4a --apply
  python remove_below_ar_cards.py --all --apply
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import is_displayable_rarity, normalize_rarity, rank_for_rarity  # noqa: E402

APPLY = "--apply" in sys.argv
ALL_SETS = "--all" in sys.argv
PAGE = 500


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    set_code = get_arg("--set", "")
    if not ALL_SETS and not set_code:
        print("사용: python remove_below_ar_cards.py --set SV4a [--apply]")
        print("      python remove_below_ar_cards.py --all [--apply]")
        return

    set_filter: dict | None = None
    if not ALL_SETS:
        s = sb.table("card_sets").select("id,set_code,name_kr").eq("set_code", set_code).single().execute()
        set_filter = s.data
        print(f"=== {set_filter['name_kr']}({set_code}) AR 미만 정리 ===")

    to_delete: list[dict] = []
    offset = 0
    while True:
        q = sb.table("cards").select("id,card_number,name_kr,rarity,set_id,card_sets(set_code,name_kr)")
        if set_filter:
            q = q.eq("set_id", set_filter["id"])
        rows = q.range(offset, offset + PAGE - 1).execute().data or []
        for row in rows:
            rarity = row.get("rarity") or ""
            if not is_displayable_rarity(rarity):
                to_delete.append(row)
        if len(rows) < PAGE:
            break
        offset += PAGE

    by_rarity: dict[str, int] = {}
    for row in to_delete:
        r = normalize_rarity(row.get("rarity") or "") or "?"
        by_rarity[r] = by_rarity.get(r, 0) + 1

    print(f"삭제 대상: {len(to_delete)}장 {dict(sorted(by_rarity.items()))}")
    if not to_delete:
        return

    for row in to_delete[:12]:
        sc = (row.get("card_sets") or {}).get("set_code", "?")
        print(f"  {sc} {row.get('card_number')} {row.get('rarity')} {row.get('name_kr')}")

    if not APPLY:
        print("\n드라이런 — 반영: --apply 추가")
        return

    ids = [r["id"] for r in to_delete]
    for i in range(0, len(ids), 100):
        batch = ids[i : i + 100]
        sb.table("prices_kr").delete().in_("card_id", batch).execute()
        sb.table("prices_jp").delete().in_("card_id", batch).execute()
        sb.table("cards").delete().in_("id", batch).execute()
        print(f"  삭제 {len(batch)}장...")

    print(f"\n완료: {len(ids)}장 및 연결 시세 삭제")


if __name__ == "__main__":
    main()
