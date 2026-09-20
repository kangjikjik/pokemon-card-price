"""전설의 고동 미등록 카드와 Collectory 번호 후보를 비교한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))
from kr_sets import COLLECTORY_IDS
from utils.db import get_supabase


def number_key(value: str | None) -> str:
    match = re.match(r"\s*0*(\d+)\s*/\s*0*(\d+)", value or "")
    return f"{int(match.group(1)):03d}/{int(match.group(2))}" if match else ""


def main() -> None:
    sb = get_supabase()
    set_row = sb.table("card_sets").select("id").eq("set_code", "S3H").single().execute().data
    cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", set_row["id"]).is_("image_url", "null").execute().data or []
    source = httpx.get(
        f"https://collectory.cc/api/sets/{COLLECTORY_IDS['S3H']}/cards",
        timeout=90,
    ).json().get("cards") or []
    report = []
    for card in cards:
        candidates = [
            {
                "card_number": row.get("card_number"),
                "name_ko": row.get("name_ko"),
                "rarity": row.get("rarity"),
                "cdn_image_url": row.get("cdn_image_url"),
            }
            for row in source
            if number_key(row.get("card_number")) == number_key(card.get("card_number"))
        ]
        report.append({"db": card, "collectory_candidates": candidates})
    print(json.dumps({"collectory_id": COLLECTORY_IDS["S3H"], "missing_count": len(cards), "cards": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
