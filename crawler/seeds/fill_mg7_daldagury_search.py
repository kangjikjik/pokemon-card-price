"""달다구리 전체 카드 검색으로 스톰에메랄다 시크릿 이미지를 보완."""
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
    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity,image_url")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )
    report = {"updated": [], "unresolved": []}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for card in cards:
            if card.get("image_url"):
                continue
            response = client.get(
                "https://api.daldagury.com/tcg/cards/search",
                params={"name": card.get("name_kr") or ""},
            )
            rows = response.json().get("resultData", {}).get("data", [])
            expected = number(card.get("card_number"))
            matches = [
                row
                for row in rows
                if row.get("setCode") == "M6"
                and number(row.get("numberInSet") or row.get("cardNumber")) == expected
                and row.get("thumbnailUrl")
            ]
            if not matches:
                report["unresolved"].append(
                    {
                        "card_id": card["id"],
                        "card_number": card.get("card_number"),
                        "name_kr": card.get("name_kr"),
                    }
                )
                continue
            source = matches[0]
            image_url = source["thumbnailUrl"].replace("_thumb.webp", "_medium.webp")
            sb.table("cards").update({"image_url": image_url}).eq(
                "id", card["id"]
            ).execute()
            report["updated"].append(
                {
                    "card_id": card["id"],
                    "card_number": card.get("card_number"),
                    "name_kr": card.get("name_kr"),
                    "image_url": image_url,
                    "source_card_id": source.get("cardId"),
                }
            )
    Path("_audit_out/mg7_daldagury_search_apply.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: len(value) for key, value in report.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
