"""울트라썬(SM4, 2018-01-17) 이전 확장팩·카드 전부 삭제."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import (
    write_constants,
    write_set_images,
    write_set_msrp,
    write_set_names,
)

CUTOFF = "2018-01-17"  # 울트라썬 발매일 — 이 날짜 미만 삭제, SM4/SM4+ 포함 유지
APPLY = "--apply" in sys.argv


def codes_to_delete() -> list[KrSet]:
    return [s for s in KR_SETS if s.released_at < CUTOFF]


def codes_to_keep() -> list[KrSet]:
    return [s for s in KR_SETS if s.released_at >= CUTOFF]


def delete_set_data(sb, set_id: int) -> tuple[int, int, int]:
    cards = sb.table("cards").select("id").eq("set_id", set_id).execute().data or []
    card_ids = [c["id"] for c in cards]
    pk = pj = 0
    # batch delete prices
    for i in range(0, len(card_ids), 100):
        batch = card_ids[i : i + 100]
        if not batch:
            break
        r1 = sb.table("prices_kr").delete().in_("card_id", batch).execute()
        r2 = sb.table("prices_jp").delete().in_("card_id", batch).execute()
        pk += len(getattr(r1, "data", None) or batch)
        pj += len(getattr(r2, "data", None) or batch)
    if card_ids:
        for i in range(0, len(card_ids), 100):
            batch = card_ids[i : i + 100]
            sb.table("cards").delete().in_("id", batch).execute()
    sb.table("card_sets").delete().eq("id", set_id).execute()
    return len(card_ids), pk, pj


def main() -> None:
    doomed = codes_to_delete()
    kept = codes_to_keep()
    print(f"CUTOFF={CUTOFF} (미만 삭제)")
    print(f"삭제 {len(doomed)}개 / 유지 {len(kept)}개")
    print("\n[삭제]")
    for s in doomed:
        print(f"  {s.released_at} {s.code:8} {s.name_kr}")
    print("\n[유지 끝부분]")
    for s in kept[-5:]:
        print(f"  {s.released_at} {s.code:8} {s.name_kr}")

    if not APPLY:
        print("\n드라이런 — 반영: python purge_pre_ultrasun.py --apply")
        return

    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    total_cards = 0
    for s in doomed:
        rows = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data or []
        if not rows:
            print(f"  {s.code}: DB에 세트 없음 (스킵)")
            continue
        set_id = rows[0]["id"]
        n, pk, pj = delete_set_data(sb, set_id)
        total_cards += n
        print(f"  {s.code}: cards={n} deleted set_id={set_id}")

    # 혹시 kr_sets에 없지만 오래된 세트가 DB에 있으면
    all_db = sb.table("card_sets").select("id,set_code,released_at,name_kr").execute().data or []
    keep_codes = {s.code for s in kept}
    for row in all_db:
        code = row.get("set_code") or ""
        if code in keep_codes:
            continue
        # featured 외 오래된 것도 발매일로 판단
        released = (row.get("released_at") or "")[:10]
        if released and released < CUTOFF:
            n, _, _ = delete_set_data(sb, row["id"])
            total_cards += n
            print(f"  EXTRA {code}: cards={n} ({released})")

    write_kr_sets(kept)
    ensure_kr_sets_footer()
    write_set_images(kept)
    write_set_names(kept)
    write_set_msrp(kept)
    write_constants([s.code for s in kept])
    print(f"\n완료: 카드 {total_cards}장 + 세트 {len(doomed)}개 삭제, 유지 {len(kept)}개")


if __name__ == "__main__":
    main()
