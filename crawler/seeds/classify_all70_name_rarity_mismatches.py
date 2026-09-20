"""70팩 잔여 카드의 이름 불일치·등급 불일치를 분리 집계한다."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase
from fill_all_70_missing_daldagury_exact import TARGETS, name_key, rarity_key


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code").in_("set_code", list(TARGETS)).execute().data or []
    }
    result = []
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, source_set_id in TARGETS.items():
            if code not in sets:
                continue
            source = client.get(f"https://api.daldagury.com/tcg/sets/{source_set_id}/cards?limit=500").json().get("resultData", {}).get("data", []) or []
            names = {name_key(row.get("nameKo")) for row in source}
            rarities = {rarity_key(row.get("lowestRarity")) for row in source}
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            for card in cards:
                if (card.get("image_url") or "").strip():
                    continue
                name_match = name_key(card.get("name_kr")) in names
                rarity_match = rarity_key(card.get("rarity")) in rarities
                if name_match and rarity_match:
                    category = "both_match_but_ambiguous"
                elif name_match:
                    category = "rarity_only_mismatch"
                elif rarity_match:
                    category = "name_only_mismatch"
                else:
                    category = "both_name_and_rarity_mismatch"
                result.append({**card, "set_code": code, "category": category})
    report = {
        "total_missing_in_70": len(result),
        "counts": dict(Counter(row["category"] for row in result)),
        "cards": result,
    }
    Path("_audit_out/classify_all70_name_rarity_mismatches.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"total_missing_in_70": report["total_missing_in_70"], "counts": report["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
