"""2018년 발매 팩과 연결된 카드·시세·박스 시세를 삭제한다."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from utils.db import get_supabase

OUT = Path("_audit_out/delete_2018_sets.json")


def delete_in_chunks(sb, table: str, column: str, values: list[int], chunk_size: int = 50) -> int:
    deleted = 0
    for start in range(0, len(values), chunk_size):
        if not values[start : start + chunk_size]:
            continue
        result = sb.table(table).delete().in_(column, values[start : start + chunk_size]).execute()
        deleted += len(result.data or [])
    return deleted


def main() -> None:
    sb = get_supabase()
    sets = (
        sb.table("card_sets")
        .select("id,set_code,name_kr,released_at,image_url")
        .gte("released_at", "2018-01-01")
        .lt("released_at", "2019-01-01")
        .order("released_at")
        .execute()
        .data
        or []
    )
    report = {"sets": [], "cards_deleted": 0, "prices_kr_deleted": 0, "prices_jp_deleted": 0, "prices_box_deleted": 0}
    for set_row in sets:
        cards = sb.table("cards").select("id,card_number,name_kr,rarity").eq("set_id", set_row["id"]).execute().data or []
        card_ids = [row["id"] for row in cards]
        prices_kr = delete_in_chunks(sb, "prices_kr", "card_id", card_ids)
        prices_jp = delete_in_chunks(sb, "prices_jp", "card_id", card_ids)
        prices_box = delete_in_chunks(sb, "prices_box", "set_id", [set_row["id"]])
        cards_deleted = delete_in_chunks(sb, "cards", "id", card_ids)
        sb.table("card_sets").delete().eq("id", set_row["id"]).execute()
        stats = {
            **set_row,
            "cards_before": len(cards),
            "cards_deleted": cards_deleted,
            "prices_kr_deleted": prices_kr,
            "prices_jp_deleted": prices_jp,
            "prices_box_deleted": prices_box,
        }
        report["sets"].append(stats)
        report["cards_deleted"] += cards_deleted
        report["prices_kr_deleted"] += prices_kr
        report["prices_jp_deleted"] += prices_jp
        report["prices_box_deleted"] += prices_box
        print(json.dumps(stats, ensure_ascii=False), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
