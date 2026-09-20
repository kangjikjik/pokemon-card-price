"""직전 작업에서 삭제한 MG7 카드 행을 이미지 없이 복구한다."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


RANK = {
    "C": 1, "U": 2, "R": 3, "RR": 4, "RRR": 5, "AR": 6,
    "SR": 7, "SAR": 8, "UR": 9, "HR": 9, "MUR": 10,
}


def main() -> None:
    sb = get_supabase()
    set_row = (
        sb.table("card_sets")
        .select("id")
        .eq("set_code", "MG7")
        .single()
        .execute()
        .data
    )
    deleted = json.loads(
        Path("_audit_out/mg7_delete_not_in_daldagury.json").read_text(encoding="utf-8")
    )["deleted"]
    restored = []
    for card in deleted:
        existing = (
            sb.table("cards")
            .select("id")
            .eq("set_id", set_row["id"])
            .eq("card_number", card["card_number"])
            .execute()
            .data
            or []
        )
        if existing:
            continue
        rows = sb.table("cards").insert(
            {
                "set_id": set_row["id"],
                "name_jp": "",
                "name_kr": card["name_kr"],
                "name_en": "",
                "rarity": card["rarity"],
                "rarity_rank": RANK.get(card["rarity"], 7),
                "image_url": None,
                "card_number": card["card_number"],
                "image_color": "from-slate-600 via-slate-700 to-slate-800",
            }
        ).execute().data or []
        restored.append({"old_id": card["id"], "new_id": rows[0]["id"]})
    Path("_audit_out/mg7_restore_deleted.json").write_text(
        json.dumps({"restored": restored}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"restored": len(restored)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
