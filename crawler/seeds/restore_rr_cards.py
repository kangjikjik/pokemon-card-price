"""
삭제된 RR 카드를 collectory에서 복구 (이미지 URL 포함).

DB에서 remove_rr_cards.py로 삭제된 경우 — collectory CDN URL을 그대로 다시 넣습니다.
처음부터 이미지를 다시 긁을 필요 없습니다.

실행:
  python restore_rr_cards.py
  python restore_rr_cards.py --apply
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from fill_oldest_rr_plus import expected_catalog, upsert_card  # noqa: E402
from kr_sets import KR_SETS  # noqa: E402

APPLY = "--apply" in sys.argv


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90, follow_redirects=True)

    sets = [s for s in KR_SETS if s.collectory_id]
    print(f"대상 세트 {len(sets)}개, apply={APPLY}\n")

    total_rr = 0
    inserted = updated = skipped = 0

    for meta in sets:
        set_row = (
            sb.table("card_sets")
            .select("id")
            .eq("set_code", meta.code)
            .single()
            .execute()
            .data
        )
        if not set_row:
            print(f"[{meta.code}] SKIP — card_sets 없음")
            continue

        set_id = set_row["id"]
        expected = expected_catalog(meta.code, meta.collectory_id, client)
        rr_items = {k: v for k, v in expected.items() if k[1] == "RR"}
        if not rr_items:
            continue

        existing = (
            sb.table("cards")
            .select("id,card_number,rarity")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        existing_rr = sum(1 for c in existing if c.get("rarity") == "RR")
        by_number: dict[str, list] = defaultdict(list)
        for row in existing:
            by_number[row.get("card_number") or ""].append(row)

        need = len(rr_items) - existing_rr
        if need <= 0:
            continue

        print(f"[{meta.code}] RR 기대 {len(rr_items)} / DB {existing_rr} → +{need}")

        if APPLY:
            for (num, rarity), card in sorted(rr_items.items()):
                action = upsert_card(sb, set_id, num, rarity, card, by_number)
                if action == "inserted":
                    inserted += 1
                elif action == "updated":
                    updated += 1
                else:
                    skipped += 1
        total_rr += need

    client.close()

    if not APPLY:
        print(f"\n드라이런 — 복구 예정 약 {total_rr}장")
        print("반영: python restore_rr_cards.py --apply")
        return

    after = sb.table("cards").select("id", count="exact").eq("rarity", "RR").execute()
    print(f"\n완료: insert {inserted}, update {updated}, skip {skipped}")
    print(f"DB RR 카드: {after.count}장")


if __name__ == "__main__":
    main()
