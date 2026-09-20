"""현재 DB에서 이미지가 비어 있는 카드 전수 집계(읽기 전용)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def load_all(sb, table: str, fields: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        batch = sb.table(table).select(fields).range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def main() -> None:
    sb = get_supabase()
    sets = load_all(sb, "card_sets", "id,set_code,name_kr,released_at")
    cards = load_all(sb, "cards", "id,set_id,card_number,name_kr,rarity,image_url")
    set_by_id = {row["id"]: row for row in sets}
    missing = [
        {
            **card,
            "set_code": set_by_id.get(card["set_id"], {}).get("set_code"),
            "set_name": set_by_id.get(card["set_id"], {}).get("name_kr"),
            "released_at": set_by_id.get(card["set_id"], {}).get("released_at"),
        }
        for card in cards
        if not (card.get("image_url") or "").strip()
    ]
    grouped: dict[str, dict] = defaultdict(lambda: {"cards": [], "count": 0})
    for card in missing:
        key = card["set_code"] or str(card["set_id"])
        grouped[key]["set_name"] = card["set_name"]
        grouped[key]["released_at"] = card["released_at"]
        grouped[key]["count"] += 1
        grouped[key]["cards"].append({
            "id": card["id"],
            "card_number": card["card_number"],
            "name_kr": card["name_kr"],
            "rarity": card["rarity"],
        })
    report = {
        "read_only": True,
        "cards_total": len(cards),
        "cards_with_images": len(cards) - len(missing),
        "missing_image_total": len(missing),
        "sets_with_missing_images": len(grouped),
        "by_set": dict(sorted(grouped.items(), key=lambda item: (item[1].get("released_at") or "", item[0]))),
    }
    out = Path("_audit_out/missing_card_images_current.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "cards_total": report["cards_total"],
        "cards_with_images": report["cards_with_images"],
        "missing_image_total": report["missing_image_total"],
        "sets_with_missing_images": report["sets_with_missing_images"],
        "by_set_counts": {code: value["count"] for code, value in report["by_set"].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
