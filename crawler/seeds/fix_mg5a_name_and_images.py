"""닌자스피너의 ex 표기 차이와 지프·마티에르 교차 연결을 보정한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

SET_CODE = "MG5a"
DALDAGURY_SET_ID = 2239
REPORT = Path("_audit_out/mg5a_name_and_images_apply.json")


def number(value: str | None) -> int | None:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else None


def without_ex(value: str | None) -> str:
    return re.sub(r"\s*ex\s*$", "", (value or "").strip(), flags=re.I)


def medium(url: str) -> str:
    return url.replace("_thumb.webp", "_medium.webp")


def main() -> None:
    sb = get_supabase()
    set_row = sb.table("card_sets").select("id").eq("set_code", SET_CODE).single().execute().data
    cards = sb.table("cards").select("id,card_number,name_kr,name_jp,name_en,rarity,image_url").eq("set_id", set_row["id"]).execute().data or []
    response = httpx.get(f"https://api.daldagury.com/tcg/sets/{DALDAGURY_SET_ID}/cards?limit=500", timeout=60)
    response.raise_for_status()
    source = response.json().get("resultData", {}).get("data", []) or []
    source_by_number = {number(row.get("numberInSet") or row.get("cardNumber")): row for row in source}
    results = []
    for card in cards:
        n = number(card.get("card_number"))
        if n not in {96, 97, 98, 99, 100, 101, 102, 103, 109, 111, 114, 115, 116, 117, 120}:
            continue
        src = source_by_number.get(n)
        if not src:
            results.append({"card_id": card["id"], "status": "unresolved", "reason": "source_missing"})
            continue
        source_name = (src.get("nameKo") or "").strip()
        source_rarity = (src.get("lowestRarity") or "").upper()
        if source_rarity and source_rarity != (card.get("rarity") or "").upper():
            results.append({"card_id": card["id"], "card_number": card.get("card_number"), "status": "unresolved", "reason": "rarity_mismatch", "db_rarity": card.get("rarity"), "daldagury_rarity": source_rarity})
            continue
        swapped_name_fix = n in {109, 111}
        name_matches = without_ex(card.get("name_kr")) == without_ex(source_name)
        if not name_matches and not swapped_name_fix:
            results.append({"card_id": card["id"], "card_number": card.get("card_number"), "status": "unresolved", "reason": "name_mismatch", "db_name": card.get("name_kr"), "daldagury_name": source_name})
            continue
        updates = {"image_url": medium(src.get("thumbnailUrl") or "")}
        if swapped_name_fix:
            updates["name_kr"] = source_name
        sb.table("cards").update(updates).eq("id", card["id"]).execute()
        results.append({"card_id": card["id"], "card_number": card.get("card_number"), "old_name_kr": card.get("name_kr"), "new_name_kr": updates.get("name_kr", card.get("name_kr")), "rarity": card.get("rarity"), "image_url": updates["image_url"], "status": "updated"})
    report = {"source": "daldagury_only", "set_code": SET_CODE, "results": results, "updated": sum(r["status"] == "updated" for r in results), "unresolved": sum(r["status"] == "unresolved" for r in results)}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
