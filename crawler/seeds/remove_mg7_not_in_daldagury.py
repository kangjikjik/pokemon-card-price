"""달다구리 스톰에메랄다 목록에 없는 DB 카드를 삭제한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def number(value: str | None) -> int | None:
    compact = re.sub(r"\s+", "", value or "")
    match = re.search(r"(\d+)(?:/|$)", compact)
    return int(match.group(1)) if match else None


def main() -> None:
    sb = get_supabase()
    set_id = (
        sb.table("card_sets")
        .select("id")
        .eq("set_code", "MG7")
        .single()
        .execute()
        .data["id"]
    )
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        source = client.get(
            "https://api.daldagury.com/tcg/sets/2744/cards?limit=500"
        ).json()["resultData"]["data"]
    source_numbers = {
        number(row.get("numberInSet") or row.get("cardNumber"))
        for row in source
    }
    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    deleted = []
    for card in cards:
        if number(card.get("card_number")) in source_numbers:
            continue
        for table in ("prices_kr", "prices_jp"):
            sb.table(table).delete().eq("card_id", card["id"]).execute()
        sb.table("cards").delete().eq("id", card["id"]).execute()
        deleted.append(card)
    report = {
        "set_code": "MG7",
        "source_set_id": 2744,
        "source_cards": len(source_numbers),
        "deleted": deleted,
    }
    Path("_audit_out/mg7_delete_not_in_daldagury.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"source_cards": len(source_numbers), "deleted": len(deleted)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
