"""70개 확장팩의 미등록 이미지를 달다구리 메타데이터 완전일치 기준으로 채운다."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

TARGETS = {
    # 첫 번째 35팩
    "MG7": 2744, "MG6": 2569, "MG5a": 2239, "MG5": 284, "MG4a": 4,
    "MG4": 5, "MG3a": 283, "MG3": 282, "MG2a": 7, "MG2": 16,
    "MG1b": 8, "MG1a": 281, "SV8a": 380, "SV8": 378, "SV7": 11,
    "SV6a": 280, "SV6": 374, "SV5a": 279, "SV5K": 26, "SV5M": 27,
    "SV4x": 278, "SV4": 277, "SV4a": 14, "SV4K": 276, "SV4M": 15,
    "SV3a": 275, "SV3": 366, "SV2a": 17, "SV2D": 273, "SV2P": 272,
    "SV1a": 271, "SV1V": 270, "SV1S": 269, "S12a": 18, "S12": 268,
    # 두 번째 35팩
    "S11a": 267, "S11": 266, "S10b": 265, "S10a": 264,
    "S9": 263, "S9a": 354, "S8": 262, "S8a": 261, "S8b": 260,
    "S7F": 350, "S7R": 20, "S7D": 344, "S6H": 342, "S6G": 256,
    "S6L": 340, "S5F": 255, "S5S": 338, "S5P": 339, "S4SV": 337,
    "S4B": 21, "S3H": 254, "S3Z": 253, "S2R": 252, "S2": 331,
    "S1a": 251, "S1W": 249, "S1H": 250, "SM12a": 324, "SM12": 248,
    "SM11b": 247, "SM11a": 246, "SM10": 37, "SM9": 315, "SM8b": 314,
    "SM9a": 313,
}


def number_key(value: str | None) -> str:
    match = re.match(r"\s*0*(\d+)\s*/\s*0*(\d+)", value or "")
    return f"{int(match.group(1)):03d}/{int(match.group(2))}" if match else ""


def name_key(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip()).casefold()


def rarity_key(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip()).upper()


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    }
    report = {
        "source": "daldagury",
        "policy": "only missing image_url; exact card number + normalized name + rarity; region unrestricted",
        "sets": {},
        "applied": [],
        "unresolved": [],
    }
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, source_set_id in TARGETS.items():
            if code not in sets:
                report["unresolved"].append({"set_code": code, "reason": "db_set_missing"})
                continue
            source = client.get(f"https://api.daldagury.com/tcg/sets/{source_set_id}/cards?limit=500").json().get("resultData", {}).get("data", []) or []
            source_by_key = {}
            for row in source:
                key = (number_key(row.get("numberInSet") or row.get("cardNumber")), name_key(row.get("nameKo")), rarity_key(row.get("lowestRarity")))
                source_by_key.setdefault(key, []).append(row)
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            stats = Counter()
            for card in cards:
                if (card.get("image_url") or "").strip():
                    stats["already_has_image"] += 1
                    continue
                key = (number_key(card.get("card_number")), name_key(card.get("name_kr")), rarity_key(card.get("rarity")))
                candidates = source_by_key.get(key, [])
                if not candidates:
                    same_number = [
                        row for row in source
                        if number_key(row.get("numberInSet") or row.get("cardNumber")) == key[0]
                    ]
                    reason = "number_not_found" if not same_number else "exact_name_or_rarity_mismatch"
                    report["unresolved"].append({
                        "set_code": code,
                        "card_id": card["id"],
                        "card_number": card.get("card_number"),
                        "name_kr": card.get("name_kr"),
                        "rarity": card.get("rarity"),
                        "reason": reason,
                        "source_candidates": [
                            {"name_kr": row.get("nameKo"), "rarity": row.get("lowestRarity")}
                            for row in same_number[:10]
                        ],
                    })
                    stats[reason] += 1
                    continue
                image = (candidates[0].get("thumbnailUrl") or "").replace("_thumb.webp", "_medium.webp")
                if not image:
                    report["unresolved"].append({**card, "set_code": code, "reason": "source_image_missing"})
                    stats["source_image_missing"] += 1
                    continue
                response = client.get(image)
                if response.status_code >= 400 or not (response.headers.get("content-type") or "").startswith("image/"):
                    report["unresolved"].append({**card, "set_code": code, "reason": f"image_http_{response.status_code}", "image_url": image})
                    stats["image_unavailable"] += 1
                    continue
                sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
                report["applied"].append({
                    "set_code": code,
                    "card_id": card["id"],
                    "card_number": card["card_number"],
                    "name_kr": card["name_kr"],
                    "rarity": card["rarity"],
                    "image_url": image,
                    "source_region_unrestricted": True,
                })
                stats["applied"] += 1
            report["sets"][code] = dict(stats)
            print(code, dict(stats), flush=True)

    report["summary"] = {
        "packs": len(TARGETS),
        "applied": len(report["applied"]),
        "unresolved": len(report["unresolved"]),
        "unresolved_by_reason": dict(Counter(row["reason"] for row in report["unresolved"])),
    }
    out = Path("_audit_out/fill_all_70_missing_daldagury_exact.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
