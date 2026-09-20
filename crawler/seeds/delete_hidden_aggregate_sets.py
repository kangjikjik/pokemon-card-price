"""사이트에 노출되지 않는 잘못 수집된 통합 세트 4개를 삭제한다."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

TARGET_CODES = ["SV1", "SV2", "SV5", "SV9"]


def delete_in_chunks(sb, table: str, column: str, values: list[int], chunk_size: int = 50) -> int:
    deleted = 0
    for start in range(0, len(values), chunk_size):
        chunk = values[start : start + chunk_size]
        if not chunk:
            continue
        deleted += len(sb.table(table).delete().in_(column, chunk).execute().data or [])
    return deleted


def main() -> None:
    sb = get_supabase()
    sets = sb.table("card_sets").select("id,set_code,name_kr,released_at").in_("set_code", TARGET_CODES).execute().data or []
    report = {"target_codes": TARGET_CODES, "sets": [], "cards_deleted": 0, "prices_kr_deleted": 0, "prices_jp_deleted": 0, "prices_box_deleted": 0}
    for set_row in sets:
        cards = sb.table("cards").select("id,card_number,name_kr,rarity").eq("set_id", set_row["id"]).execute().data or []
        card_ids = [row["id"] for row in cards]
        stats = {
            **set_row,
            "cards_before": len(cards),
            "prices_kr_deleted": delete_in_chunks(sb, "prices_kr", "card_id", card_ids),
            "prices_jp_deleted": delete_in_chunks(sb, "prices_jp", "card_id", card_ids),
            "prices_box_deleted": delete_in_chunks(sb, "prices_box", "set_id", [set_row["id"]]),
            "cards_deleted": delete_in_chunks(sb, "cards", "id", card_ids),
        }
        sb.table("card_sets").delete().eq("id", set_row["id"]).execute()
        report["sets"].append(stats)
        for key in ("cards_deleted", "prices_kr_deleted", "prices_jp_deleted", "prices_box_deleted"):
            report[key] += stats[key]

    remaining = sb.table("card_sets").select("id,set_code").in_("set_code", TARGET_CODES).execute().data or []
    report["remaining_sets"] = remaining
    out = Path("_audit_out/delete_hidden_aggregate_sets.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
