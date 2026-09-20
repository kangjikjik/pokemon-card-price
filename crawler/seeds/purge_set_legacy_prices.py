"""세트 카드·박스 가격 중 URL 없는 집계/Collectory 레거시 row 삭제."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from utils.db import get_supabase

sb = get_supabase()

VALID_KR = re.compile(r"^(sold|listing):bunjang:\d+")
VALID_JP = re.compile(r"^(sold|listing):bunjang:\d+|^sold:snkrdunk:\d+")
VALID_BOX = re.compile(r"^bunjang:(sold|listing):\d+")


def purge_card_table(table: str, card_ids: list[int], valid: re.Pattern[str]) -> int:
    deleted = 0
    for i in range(0, len(card_ids), 50):
        chunk = card_ids[i : i + 50]
        offset = 0
        while True:
            rows = (
                sb.table(table)
                .select("id, source")
                .in_("card_id", chunk)
                .range(offset, offset + 999)
                .execute()
                .data
                or []
            )
            if not rows:
                break
            bad_ids = [r["id"] for r in rows if not valid.match(r.get("source") or "")]
            for j in range(0, len(bad_ids), 100):
                batch = bad_ids[j : j + 100]
                if batch:
                    sb.table(table).delete().in_("id", batch).execute()
                    deleted += len(batch)
            if len(rows) < 1000:
                break
            offset += 1000
    return deleted


def purge_box(set_id: int) -> int:
    deleted = 0
    offset = 0
    while True:
        rows = (
            sb.table("prices_box")
            .select("id, source")
            .eq("set_id", set_id)
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        if not rows:
            break
        bad_ids = [r["id"] for r in rows if not VALID_BOX.match(r.get("source") or "")]
        for j in range(0, len(bad_ids), 100):
            batch = bad_ids[j : j + 100]
            if batch:
                sb.table("prices_box").delete().in_("id", batch).execute()
                deleted += len(batch)
        if len(rows) < 1000:
            break
        offset += 1000
    return deleted


def main() -> None:
    set_code = sys.argv[1] if len(sys.argv) > 1 else "MG6"
    row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).execute().data
    if not row:
        print(f"{set_code}: not found")
        return
    set_id = row[0]["id"]
    name = row[0]["name_kr"]
    cards = sb.table("cards").select("id").eq("set_id", set_id).execute().data or []
    card_ids = [c["id"] for c in cards]

    kr = purge_card_table("prices_kr", card_ids, VALID_KR)
    jp = purge_card_table("prices_jp", card_ids, VALID_JP)
    box = purge_box(set_id)
    print(f"{set_code} ({name}) 레거시 삭제: prices_kr {kr}, prices_jp {jp}, prices_box {box}")


if __name__ == "__main__":
    main()
