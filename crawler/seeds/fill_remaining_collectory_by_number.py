"""남은 지정 세트의 미등록 이미지를 Collectory 카드번호 기준으로 채운다."""
from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase
from kr_sets import COLLECTORY_IDS

TARGETS = [
    "SM10", "SM11a", "SM12", "S3Z", "S5P", "SM8b", "SM9", "S1H",
    "SM11b", "S2", "S1a", "S8b", "MG7", "S6H", "S4SV", "S6G",
    "S6L", "S7D", "S7R", "S9", "S11",
]


def number_key(value: str | None) -> str:
    match = re.match(r"\s*0*(\d+)\s*/\s*0*(\d+)", value or "")
    return f"{int(match.group(1)):03d}/{int(match.group(2))}" if match else ""


def rarity_key(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").upper())


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", TARGETS).execute().data or []
    }
    report = {"policy": "Collectory card number match; rarity preferred; name ignored", "applied": [], "unresolved": [], "sets": {}}
    with httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code in TARGETS:
            if code not in sets or not COLLECTORY_IDS.get(code):
                continue
            source = client.get(f"https://collectory.cc/api/sets/{COLLECTORY_IDS[code]}/cards", timeout=90).json().get("cards") or []
            by_number = {}
            for row in source:
                if row.get("region") == "kr":
                    by_number.setdefault(number_key(row.get("card_number")), []).append(row)
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            stats = Counter()
            for card in cards:
                if (card.get("image_url") or "").strip():
                    continue
                candidates = by_number.get(number_key(card.get("card_number")), [])
                if not candidates:
                    report["unresolved"].append({**card, "set_code": code, "reason": "number_not_found"})
                    stats["number_not_found"] += 1
                    continue
                same_rarity = [row for row in candidates if rarity_key(row.get("rarity")) == rarity_key(card.get("rarity"))]
                selected = same_rarity if same_rarity else candidates
                urls = list(dict.fromkeys((row.get("cdn_image_url") or "") for row in selected if "/cards/kr/" in (row.get("cdn_image_url") or "")))
                if len(urls) != 1:
                    report["unresolved"].append({**card, "set_code": code, "reason": "multiple_or_missing_candidates", "candidate_names": [row.get("name_ko") for row in selected], "candidate_urls": urls})
                    stats["multiple_or_missing_candidates"] += 1
                    continue
                image = urls[0]
                try:
                    response = client.get(image)
                    response.raise_for_status()
                    with Image.open(io.BytesIO(response.content)) as img:
                        img.verify()
                except Exception as exc:
                    report["unresolved"].append({**card, "set_code": code, "reason": f"invalid_image:{exc}", "candidate_url": image})
                    stats["invalid_image"] += 1
                    continue
                sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
                report["applied"].append({**card, "set_code": code, "image_url": image, "collectory_name": selected[0].get("name_ko"), "collectory_rarity": selected[0].get("rarity")})
                stats["applied"] += 1
            report["sets"][code] = dict(stats)
            print(code, dict(stats), flush=True)
    report["summary"] = {"packs": len(TARGETS), "applied": len(report["applied"]), "unresolved": len(report["unresolved"]), "unresolved_by_reason": dict(Counter(row["reason"] for row in report["unresolved"]))}
    out = Path("_audit_out/fill_remaining_collectory_by_number.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
