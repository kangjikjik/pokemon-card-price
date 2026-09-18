"""DB 카드 이미지와 pokemoncard.co.kr 공식 이미지의 읽기 전용 전수 대조."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from fix_unpriced_card_identity import _fetch_one
from kr_sets import KR_SETS
from utils.db import get_supabase

OUT = Path("_audit_out/db_card_image_audit.json")


def _load_cards(sb, set_id: int) -> list[dict]:
    out: list[dict] = []
    start = 0
    while True:
        rows = (
            sb.table("cards")
            .select("id,card_number,name_kr,rarity,image_url")
            .eq("set_id", set_id)
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        out.extend(rows)
        if len(rows) < 1000:
            return out
        start += 1000


def _image_key(url: str) -> str:
    parsed = urlsplit((url or "").split("?", 1)[0])
    return parsed.path.casefold().rstrip("/")


def main() -> None:
    sb = get_supabase()
    set_ids = {
        row["set_code"]: row["id"]
        for row in (sb.table("card_sets").select("id,set_code").execute().data or [])
    }
    targets: list[dict] = []
    for meta in KR_SETS:
        if meta.code not in set_ids or not meta.bs_code:
            continue
        targets.extend(
            {
                **card,
                "set": meta.name_kr,
                "set_code": meta.code,
                "bs_code": meta.bs_code,
            }
            for card in _load_cards(sb, set_ids[meta.code])
        )

    def audit(card: dict) -> dict:
        result = _fetch_one(card["bs_code"], card)
        if result.get("status") != "matched":
            return {
                "status": "unmatched",
                "set": card["set"],
                "set_code": card["set_code"],
                "card_id": card["id"],
                "card_number": card.get("card_number"),
                "name_kr": card.get("name_kr"),
                "rarity": card.get("rarity"),
                "reason": result.get("reason", result.get("status", "")),
            }
        official = result["official"]
        db_key = _image_key(card.get("image_url") or "")
        official_key = _image_key(official.get("image_url") or "")
        if db_key == official_key:
            return {"status": "match"}
        return {
            "status": "mismatch",
            "set": card["set"],
            "set_code": card["set_code"],
            "card_id": card["id"],
            "card_number": card.get("card_number"),
            "name_kr": card.get("name_kr"),
            "rarity": card.get("rarity"),
            "db_image_url": card.get("image_url") or "",
            "official_image_url": official.get("image_url") or "",
            "official_name_kr": official.get("name_kr") or "",
            "official_printed": official.get("printed") or "",
        }

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(audit, card) for card in targets]
        for future in as_completed(futures):
            results.append(future.result())

    mismatches = [row for row in results if row.get("status") == "mismatch"]
    unmatched = [row for row in results if row.get("status") == "unmatched"]
    body = {
        "cards_checked": len(targets),
        "matches": len(targets) - len(mismatches) - len(unmatched),
        "mismatches": len(mismatches),
        "unmatched": len(unmatched),
        "mismatch_samples": mismatches[:10],
        "unmatched_samples": unmatched[:10],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
