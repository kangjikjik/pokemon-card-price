"""첫 35개 확장팩에 달다구리 한국판 이미지만 안전하게 적용."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

DALDAGURY_API = "https://api.daldagury.com"
REPORT = Path("_audit_out/daldagury_batch1_35_verified_apply.json")
TARGETS = {
    "MG7": 2744, "MG6": 2569, "MG5a": 2239, "MG5": 284, "MG4a": 4,
    "MG4": 5, "MG3a": 283, "MG3": 282, "MG2a": 7, "MG2": 16,
    "MG1b": 8, "MG1a": 281, "SV8a": 380, "SV8": 378, "SV7": 11,
    "SV6a": 280, "SV6": 374, "SV5a": 279, "SV5K": 26, "SV5M": 27,
    "SV4x": 278, "SV4": 277, "SV4a": 14, "SV4K": 276, "SV4M": 15,
    "SV3a": 275, "SV3": 366, "SV2a": 17, "SV2D": 273, "SV2P": 272,
    "SV1a": 271, "SV1V": 270, "SV1S": 269, "S12a": 18, "S12": 268,
}


def number(value: str | None) -> int | None:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else None


def norm_name(value: str | None) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (value or "").casefold())


def medium(url: str | None) -> str:
    return (url or "").replace("_thumb.webp", "_medium.webp")


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    }
    report = {
        "source": "daldagury_only",
        "policy": "apply only verified Korean-name matches; Japanese/missing/ambiguous images remain empty; no Collectory",
        "sets": {},
        "updated": [],
        "unresolved": [],
        "source_only": [],
        "duplicates": [],
    }
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, source_set_id in TARGETS.items():
            if code not in sets:
                report["unresolved"].append({"set_code": code, "reason": "db_set_missing"})
                continue
            response = client.get(f"{DALDAGURY_API}/tcg/sets/{source_set_id}/cards?limit=500")
            response.raise_for_status()
            source = response.json().get("resultData", {}).get("data", []) or []
            by_number: dict[int, list[dict]] = defaultdict(list)
            for row in source:
                n = number(row.get("numberInSet") or row.get("cardNumber"))
                if n is not None:
                    by_number[n].append(row)

            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            duplicate_keys = [
                key for key, count in Counter(
                    ((number(row.get("card_number")), (row.get("rarity") or "").upper()) for row in cards)
                ).items() if key[0] is not None and count > 1
            ]
            for key in duplicate_keys:
                report["duplicates"].append({"set_code": code, "card_number": key[0], "rarity": key[1]})

            seen_numbers: set[int] = set()
            stats = {"source_cards": len(source), "db_cards": len(cards), "updated": 0, "unchanged": 0, "unresolved": 0, "name_mismatch": 0, "rarity_mismatch": 0, "missing_source_number": 0}
            for card in cards:
                n = number(card.get("card_number"))
                candidates = by_number.get(n, []) if n is not None else []
                if not candidates:
                    stats["missing_source_number"] += 1
                    stats["unresolved"] += 1
                    report["unresolved"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "name_kr": card.get("name_kr"), "rarity": card.get("rarity"), "reason": "daldagury_number_not_found"})
                    continue
                seen_numbers.add(n)
                db_rarity = (card.get("rarity") or "").upper()
                source_card = next((row for row in candidates if (row.get("lowestRarity") or "").upper() == db_rarity), None)
                if source_card is None and len(candidates) == 1:
                    source_card = candidates[0]
                if source_card is None:
                    stats["rarity_mismatch"] += 1
                    stats["unresolved"] += 1
                    report["unresolved"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "name_kr": card.get("name_kr"), "rarity": card.get("rarity"), "reason": "ambiguous_source_rarity", "source_candidates": [{"name_kr": r.get("nameKo"), "lowest_rarity": r.get("lowestRarity")} for r in candidates]})
                    continue
                source_name = source_card.get("nameKo") or ""
                if source_name and norm_name(source_name) != norm_name(card.get("name_kr")):
                    stats["name_mismatch"] += 1
                    stats["unresolved"] += 1
                    report["unresolved"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "db_name_kr": card.get("name_kr"), "daldagury_name_kr": source_name, "rarity": card.get("rarity"), "reason": "name_mismatch"})
                    continue
                source_lowest = (source_card.get("lowestRarity") or "").upper()
                if source_lowest and source_lowest != db_rarity:
                    stats["rarity_mismatch"] += 1
                    stats["unresolved"] += 1
                    report["unresolved"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "name_kr": card.get("name_kr"), "db_rarity": card.get("rarity"), "daldagury_rarity": source_card.get("lowestRarity"), "reason": "rarity_mismatch"})
                    continue
                image = medium(source_card.get("thumbnailUrl"))
                if not image:
                    stats["unresolved"] += 1
                    report["unresolved"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "name_kr": card.get("name_kr"), "rarity": card.get("rarity"), "reason": "daldagury_image_missing"})
                    continue
                try:
                    response = client.get(image)
                    if response.status_code != 200 or not (response.headers.get("content-type") or "").startswith("image/"):
                        raise RuntimeError(f"http_{response.status_code}_{response.headers.get('content-type', '')}")
                except Exception as exc:
                    stats["unresolved"] += 1
                    report["unresolved"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "name_kr": card.get("name_kr"), "rarity": card.get("rarity"), "candidate_url": image, "reason": str(exc)})
                    continue
                if card.get("image_url") == image:
                    stats["unchanged"] += 1
                else:
                    sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
                    stats["updated"] += 1
                    report["updated"].append({"set_code": code, "card_id": card["id"], "card_number": card.get("card_number"), "name_kr": card.get("name_kr"), "rarity": card.get("rarity"), "image_url": image, "source_card_id": source_card.get("cardId")})

            for n, rows in by_number.items():
                if n not in seen_numbers and rows:
                    report["source_only"].append({"set_code": code, "card_number": rows[0].get("numberInSet"), "name_kr": rows[0].get("nameKo"), "lowest_rarity": rows[0].get("lowestRarity"), "reason": "daldagury_card_not_in_db"})
            report["sets"][code] = stats
            print(code, json.dumps(stats, ensure_ascii=False), flush=True)

    report["summary"] = {key: sum(stats.get(key, 0) for stats in report["sets"].values()) for key in ("source_cards", "db_cards", "updated", "unchanged", "unresolved", "name_mismatch", "rarity_mismatch", "missing_source_number")}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
