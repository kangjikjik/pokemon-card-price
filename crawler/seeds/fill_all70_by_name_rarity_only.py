"""70팩 미등록 이미지를 카드번호 무시, 이름·등급 일치 기준으로 채운다."""
from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase
from fill_all_70_missing_daldagury_exact import TARGETS, name_key, rarity_key


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    }
    report = {"policy": "ignore card number; require exact normalized name and rarity", "applied": [], "unresolved": [], "sets": {}}
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, source_set_id in TARGETS.items():
            if code not in sets:
                continue
            source = client.get(f"https://api.daldagury.com/tcg/sets/{source_set_id}/cards?limit=500").json().get("resultData", {}).get("data", []) or []
            by_key = {}
            for row in source:
                key = (name_key(row.get("nameKo")), rarity_key(row.get("lowestRarity")))
                by_key.setdefault(key, []).append(row)
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            stats = Counter()
            for card in cards:
                if (card.get("image_url") or "").strip():
                    continue
                key = (name_key(card.get("name_kr")), rarity_key(card.get("rarity")))
                candidates = by_key.get(key, [])
                if not candidates:
                    report["unresolved"].append({**card, "set_code": code, "reason": "name_or_rarity_mismatch"})
                    stats["name_or_rarity_mismatch"] += 1
                    continue
                unique_urls = list(dict.fromkeys((row.get("thumbnailUrl") or "").replace("_thumb.webp", "_medium.webp") for row in candidates))
                unique_urls = [url for url in unique_urls if url]
                if len(unique_urls) != 1:
                    report["unresolved"].append({**card, "set_code": code, "reason": "multiple_name_rarity_candidates", "candidate_urls": unique_urls})
                    stats["multiple_candidates"] += 1
                    continue
                image = unique_urls[0]
                try:
                    response = client.get(image)
                    response.raise_for_status()
                    if not (response.headers.get("content-type") or "").startswith("image/"):
                        raise ValueError("not_image_content_type")
                    with Image.open(io.BytesIO(response.content)) as img:
                        img.verify()
                except Exception as exc:
                    report["unresolved"].append({**card, "set_code": code, "reason": f"invalid_image:{exc}", "candidate_url": image})
                    stats["invalid_image"] += 1
                    continue
                sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
                report["applied"].append({**card, "set_code": code, "image_url": image})
                stats["applied"] += 1
            report["sets"][code] = dict(stats)
            print(code, dict(stats), flush=True)
    report["summary"] = {
        "packs": len(TARGETS),
        "applied": len(report["applied"]),
        "unresolved": len(report["unresolved"]),
        "unresolved_by_reason": dict(Counter(row["reason"] for row in report["unresolved"])),
    }
    out = Path("_audit_out/fill_all70_by_name_rarity_only.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
