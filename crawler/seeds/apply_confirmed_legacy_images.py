"""달다구리 전체 검색에서 번호까지 확인된 카드 이미지만 적용한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


SETS = {
    "S8b": "S8b",
    "S4SV": "S4a",
    "S4B": "S4",
    "S3H": "S3a",
}


def number(value: str | None) -> int | None:
    compact = re.sub(r"\s+", "", value or "")
    match = re.search(r"(\d+)", compact)
    return int(match.group(1)) if match else None


def main() -> None:
    sb = get_supabase()
    set_rows = {
        row["set_code"]: row
        for row in sb.table("card_sets")
        .select("id,set_code")
        .in_("set_code", list(SETS))
        .execute()
        .data
        or []
    }
    report = {"updated": [], "not_found": []}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for code, source_code in SETS.items():
            cards = (
                sb.table("cards")
                .select("id,card_number,name_kr,image_url")
                .eq("set_id", set_rows[code]["id"])
                .execute()
                .data
                or []
            )
            for card in cards:
                if card.get("image_url"):
                    continue
                rows = client.get(
                    "https://api.daldagury.com/tcg/cards/search",
                    params={"name": card.get("name_kr") or ""},
                ).json().get("resultData", {}).get("data", [])
                matches = [
                    row
                    for row in rows
                    if row.get("setCode") == source_code
                    and number(row.get("numberInSet") or row.get("cardNumber"))
                    == number(card.get("card_number"))
                    and row.get("thumbnailUrl")
                ]
                if not matches:
                    report["not_found"].append(
                        {"set_code": code, "card_id": card["id"], "card_number": card.get("card_number")}
                    )
                    continue
                image_url = matches[0]["thumbnailUrl"].replace("_thumb.webp", "_medium.webp")
                sb.table("cards").update({"image_url": image_url}).eq(
                    "id", card["id"]
                ).execute()
                report["updated"].append(
                    {"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "image_url": image_url}
                )
    Path("_audit_out/confirmed_legacy_images_apply.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: len(value) for key, value in report.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
