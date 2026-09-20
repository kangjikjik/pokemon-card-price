"""70팩 전체에서 사이트가 차단하는 pokemontcg.io 이미지 URL을 제거한다."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase
from fill_all_70_missing_daldagury_exact import TARGETS


def main() -> None:
    sb = get_supabase()
    sets = sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    set_by_id = {row["id"]: row for row in sets}
    cards = []
    for set_row in sets:
        cards.extend(
            sb.table("cards")
            .select("id,set_id,card_number,name_kr,rarity,image_url")
            .eq("set_id", set_row["id"])
            .execute()
            .data
            or []
        )
    blocked = [
        row for row in cards
        if "images.pokemontcg.io" in (row.get("image_url") or "")
    ]
    for row in blocked:
        sb.table("cards").update({"image_url": None}).eq("id", row["id"]).execute()
    report = {
        "scope": "all_70_packs",
        "blocked_source": "images.pokemontcg.io",
        "cleared": len(blocked),
        "by_set": dict(sorted(Counter(set_by_id[row["set_id"]]["set_code"] for row in blocked).items())),
        "cards": [
            {
                "id": row["id"],
                "set_code": set_by_id[row["set_id"]]["set_code"],
                "card_number": row["card_number"],
                "name_kr": row["name_kr"],
                "rarity": row["rarity"],
                "old_image_url": row["image_url"],
            }
            for row in blocked
        ],
    }
    out = Path("_audit_out/clear_all70_blocked_images.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cleared": report["cleared"], "by_set": report["by_set"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
