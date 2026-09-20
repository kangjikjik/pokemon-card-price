"""MG6 공식 한글명 교정 (번개 검색 alias와 별도 — 화면 표시용)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

from lib.bunjang_market_names import KR_DISPLAY_FIXUPS
from lib.price_search import normalize_mega_spelling
from utils.db import get_supabase

APPLY = "--apply" in sys.argv


def main() -> None:
    sb = get_supabase()
    row = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute().data
    if not row:
        print("MG6 없음")
        return
    set_id = row["id"]
    cards = (
        sb.table("cards")
        .select("id,name_kr,name_jp")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    updates: list[tuple[int, str, str]] = []
    for c in cards:
        old = (c.get("name_kr") or "").strip()
        new = KR_DISPLAY_FIXUPS.get(old, old)
        new = normalize_mega_spelling(new)
        if new and new != old:
            updates.append((c["id"], old, new))

    if not updates:
        print("교정 대상 없음")
        return

    for cid, old, new in updates:
        print(f"  [{cid}] {old!r} → {new!r}")

    if APPLY:
        for cid, _, new in updates:
            sb.table("cards").update({"name_kr": new}).eq("id", cid).execute()
        print(f"적용: {len(updates)}장")
    else:
        print(f"드라이런 {len(updates)}장 — --apply 로 반영")


if __name__ == "__main__":
    main()
