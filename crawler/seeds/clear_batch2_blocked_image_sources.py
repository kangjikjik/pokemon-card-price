"""사이트에서 차단되는 비공식 이미지 출처를 두 번째 35팩에서 제거한다."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

TARGETS = {
    "S11a", "S11", "S10b", "S10a", "S9", "S9a", "S8", "S8a", "S8b",
    "S7F", "S7R", "S7D", "S6H", "S6G", "S6L", "S5F", "S5S", "S5P",
    "S4SV", "S4B", "S3H", "S3Z", "S2R", "S2", "S1a", "S1W", "S1H",
    "SM12a", "SM12", "SM11b", "SM11a", "SM10", "SM9", "SM8b", "SM9a",
}
BLOCKED_HOSTS = ("images.pokemontcg.io",)


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
        if any(host in (row.get("image_url") or "") for host in BLOCKED_HOSTS)
    ]
    by_set = Counter(set_by_id[row["set_id"]]["set_code"] for row in blocked)
    for row in blocked:
        sb.table("cards").update({"image_url": None}).eq("id", row["id"]).execute()
    report = {
        "scope": "batch2_35_daldagury",
        "blocked_hosts": list(BLOCKED_HOSTS),
        "cleared": len(blocked),
        "by_set": dict(sorted(by_set.items())),
        "cards": [
            {
                **{key: row.get(key) for key in ("id", "card_number", "name_kr", "rarity", "image_url")},
                "set_code": set_by_id[row["set_id"]]["set_code"],
            }
            for row in blocked
        ],
    }
    out = Path("_audit_out/clear_batch2_blocked_image_sources.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cleared": report["cleared"], "by_set": report["by_set"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
