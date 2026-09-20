"""세트별 카드번호 중복을 가격 이력이 많은 행 하나로 통합한다."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


SET_CODES = [
    "MG6", "MG5a", "MG5", "MG4a", "MG4", "MG3a", "MG3",
    "MG2", "MG2a", "MG1b", "MG1a", "SV8a", "SV8", "SV7",
    "SV6a", "SV6", "SV5a", "SV5K", "SV5M", "SV4x", "SV4",
    "SV4a", "SV4K", "SV4M", "SV3a", "SV3", "SV2a", "SV2D",
    "SV2P", "SV1a", "SV1V", "SV1S", "S12a", "S12", "S11a",
    "S11", "S10b",
]


def card_number_key(value: str | None) -> int | None:
    compact = re.sub(r"\s+", "", value or "")
    match = re.search(r"(\d+)(?:/|$)", compact)
    return int(match.group(1)) if match else None


def price_count(sb, table: str, card_id: int) -> int:
    return len(
        sb.table(table)
        .select("id")
        .eq("card_id", card_id)
        .execute()
        .data
        or []
    )


def main() -> None:
    sb = get_supabase()
    sets = (
        sb.table("card_sets")
        .select("id,set_code")
        .in_("set_code", SET_CODES)
        .execute()
        .data
        or []
    )
    deleted: list[dict] = []
    groups = 0

    for set_row in sets:
        cards = (
            sb.table("cards")
            .select("id,card_number,name_kr,rarity,image_url")
            .eq("set_id", set_row["id"])
            .execute()
            .data
            or []
        )
        by_number: dict[int, list[dict]] = defaultdict(list)
        for card in cards:
            key = card_number_key(card.get("card_number"))
            if key is not None:
                by_number[key].append(card)

        for card_number, rows in by_number.items():
            if len(rows) < 2:
                continue
            groups += 1
            scored = []
            for row in rows:
                kr = price_count(sb, "prices_kr", row["id"])
                jp = price_count(sb, "prices_jp", row["id"])
                scored.append((kr + jp, kr, jp, -row["id"], row))
            scored.sort(reverse=True)
            keep = scored[0][4]
            for _, kr, jp, _, row in scored[1:]:
                for table in ("prices_kr", "prices_jp"):
                    sb.table(table).delete().eq("card_id", row["id"]).execute()
                sb.table("cards").delete().eq("id", row["id"]).execute()
                deleted.append(
                    {
                        "set_code": set_row["set_code"],
                        "card_number": card_number,
                        "deleted_card_id": row["id"],
                        "kept_card_id": keep["id"],
                        "deleted_prices_kr": kr,
                        "deleted_prices_jp": jp,
                    }
                )

    report = {
        "duplicate_groups": groups,
        "deleted_cards": len(deleted),
        "deleted": deleted,
    }
    Path("_audit_out/card_dedupe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "deleted"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
