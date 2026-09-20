"""다음 20개 세트를 달다구리 기준으로 이름·누락 카드를 보정한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


TARGETS = {
    "MG7": 2744, "S10a": 264, "S9a": 354, "S9": 263, "S8": 262,
    "S8a": 261, "S8b": 260, "S7F": 350, "CEL": 258, "S7R": 20,
    "S7D": 344, "S6H": 342, "S6G": 256, "S6L": 340, "S5F": 255,
    "S5S": 338, "S5P": 339, "S4SV": 337, "S4B": 21, "S3H": 254,
}
HIGH = {
    "RR", "RRR", "BWR", "AR", "CHR", "CSR", "SSR", "SR", "TR",
    "MA", "ACE", "SAR", "PR", "UR", "HR", "MUR", "FUR",
}
RANK = {
    "C": 1, "U": 2, "R": 3, "RR": 4, "RRR": 5, "AR": 6, "CHR": 6,
    "SR": 7, "SAR": 8, "UR": 9, "HR": 9, "CSR": 9, "MUR": 10,
    "PR": 6, "SSR": 9,
}


def number(value: str | None) -> int | None:
    compact = re.sub(r"\s+", "", value or "")
    match = re.search(r"(\d+)(?:/|$)", compact)
    return int(match.group(1)) if match else None


def medium(url: str | None) -> str:
    return (url or "").replace("_thumb.webp", "_medium.webp")


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets")
        .select("id,set_code")
        .in_("set_code", list(TARGETS))
        .execute()
        .data
        or []
    }
    report = {"added": [], "renamed": [], "image_filled": [], "unresolved": []}

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for code, source_id in TARGETS.items():
            source = client.get(
                f"https://api.daldagury.com/tcg/sets/{source_id}/cards?limit=500"
            ).json()["resultData"]["data"]
            by_number: dict[int, list[dict]] = {}
            for row in source:
                n = number(row.get("numberInSet") or row.get("cardNumber"))
                if n is not None:
                    by_number.setdefault(n, []).append(row)

            cards = (
                sb.table("cards")
                .select("id,card_number,name_kr,rarity,image_url")
                .eq("set_id", sets[code]["id"])
                .execute()
                .data
                or []
            )
            db_numbers = {number(card.get("card_number")) for card in cards}

            for card in cards:
                n = number(card.get("card_number"))
                candidates = by_number.get(n, []) if n is not None else []
                if not candidates:
                    continue
                source_card = next(
                    (
                        row
                        for row in candidates
                        if (row.get("lowestRarity") or "").upper()
                        == (card.get("rarity") or "").upper()
                    ),
                    candidates[0],
                )
                updates = {}
                source_name = source_card.get("nameKo") or ""
                if source_name and source_name != (card.get("name_kr") or ""):
                    updates["name_kr"] = source_name
                    report["renamed"].append(
                        {
                            "set_code": code,
                            "card_id": card["id"],
                            "card_number": card.get("card_number"),
                            "old_name": card.get("name_kr"),
                            "new_name": source_name,
                        }
                    )
                if not card.get("image_url") and source_card.get("thumbnailUrl"):
                    updates["image_url"] = medium(source_card["thumbnailUrl"])
                    report["image_filled"].append(
                        {"set_code": code, "card_id": card["id"], "image_url": updates["image_url"]}
                    )
                if updates:
                    sb.table("cards").update(updates).eq("id", card["id"]).execute()

            # Add high-rarity cards that Daldagury explicitly lists but DB lacks.
            for source_card in source:
                n = number(source_card.get("numberInSet") or source_card.get("cardNumber"))
                rarity = (source_card.get("lowestRarity") or "").upper()
                if n is None or rarity not in HIGH or n in db_numbers:
                    continue
                card_number = source_card.get("numberInSet") or source_card.get("cardNumber")
                image_url = medium(source_card.get("thumbnailUrl"))
                if not image_url:
                    report["unresolved"].append(
                        {"set_code": code, "card_number": card_number, "reason": "no_source_image"}
                    )
                    continue
                inserted = sb.table("cards").insert(
                    {
                        "set_id": sets[code]["id"],
                        "name_jp": "",
                        "name_kr": source_card.get("nameKo") or "",
                        "name_en": "",
                        "rarity": rarity,
                        "rarity_rank": RANK.get(rarity, 7),
                        "image_url": image_url,
                        "card_number": card_number,
                        "image_color": "from-slate-600 via-slate-700 to-slate-800",
                    }
                ).execute().data or []
                report["added"].append(
                    {
                        "set_code": code,
                        "card_id": inserted[0]["id"],
                        "card_number": card_number,
                        "name_kr": source_card.get("nameKo"),
                        "rarity": rarity,
                    }
                )
                db_numbers.add(n)

    Path("_audit_out/legacy_20_daldagury_repair.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: len(value) for key, value in report.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
