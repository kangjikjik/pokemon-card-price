"""DB cards.rarity_rank 를 crawler/lib/rarity_rank.py 기준으로 전부 재동기화."""
from __future__ import annotations

import os
import sys
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import RARITY_RANK, normalize_rarity, rank_for_rarity

APPLY = "--apply" in sys.argv
PAGE = 1000


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    by_rarity: dict[str, list[int]] = defaultdict(list)
    offset = 0
    while True:
        rows = (
            sb.table("cards")
            .select("id,rarity,rarity_rank")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
            or []
        )
        if not rows:
            break
        for c in rows:
            rar = normalize_rarity(c.get("rarity"))
            want = rank_for_rarity(rar)
            got = c.get("rarity_rank") or 0
            if want != got:
                by_rarity[rar].append(c["id"])
        if len(rows) < PAGE:
            break
        offset += PAGE

    total = sum(len(v) for v in by_rarity.values())
    print(f"갱신 대상 {total}장 / 등급 {len(by_rarity)}종")
    for rar in sorted(by_rarity, key=lambda r: -RARITY_RANK.get(r, -1)):
        print(f"  {rar:6} rank={rank_for_rarity(rar):2}  cards={len(by_rarity[rar])}")

    if not APPLY:
        print("\n드라이런 — 반영: python sync_rarity_ranks.py --apply")
        return

    updated = 0
    for rar, ids in by_rarity.items():
        rank = rank_for_rarity(rar)
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            sb.table("cards").update({"rarity_rank": rank}).in_("id", batch).execute()
            updated += len(batch)
        print(f"  {rar} -> {rank} ({len(ids)})")
    print(f"\n완료: {updated}장 rarity_rank 동기화")


if __name__ == "__main__":
    main()
