"""오류 없는 달다구리 이미지로 70팩의 빈 이미지 URL을 재충전한다."""
from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase
from fill_all_70_missing_daldagury_exact import TARGETS, name_key, number_key, rarity_key


def safe_daldagury_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return "daldagury" in host and "pokemontcg.io" not in host


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    }
    report = {"applied": [], "unresolved": [], "sets": {}}
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, source_set_id in TARGETS.items():
            if code not in sets:
                continue
            source = client.get(f"https://api.daldagury.com/tcg/sets/{source_set_id}/cards?limit=500").json().get("resultData", {}).get("data", []) or []
            by_key = {}
            for row in source:
                key = (number_key(row.get("numberInSet") or row.get("cardNumber")), name_key(row.get("nameKo")), rarity_key(row.get("lowestRarity")))
                by_key.setdefault(key, []).append(row)
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            stats = Counter()
            for card in cards:
                if (card.get("image_url") or "").strip():
                    continue
                key = (number_key(card.get("card_number")), name_key(card.get("name_kr")), rarity_key(card.get("rarity")))
                candidates = by_key.get(key, [])
                if not candidates:
                    stats["metadata_unmatched"] += 1
                    report["unresolved"].append({**card, "set_code": code, "reason": "metadata_unmatched"})
                    continue
                image = (candidates[0].get("thumbnailUrl") or "").replace("_thumb.webp", "_medium.webp")
                if not safe_daldagury_url(image):
                    stats["blocked_source"] += 1
                    report["unresolved"].append({**card, "set_code": code, "reason": "blocked_or_non_daldagury_source", "candidate_url": image})
                    continue
                response = client.get(image)
                try:
                    response.raise_for_status()
                    if not (response.headers.get("content-type") or "").startswith("image/"):
                        raise ValueError("not_image_content_type")
                    with Image.open(io.BytesIO(response.content)) as img:
                        img.verify()
                except Exception as exc:
                    stats["invalid_image"] += 1
                    report["unresolved"].append({**card, "set_code": code, "reason": f"invalid_image:{exc}", "candidate_url": image})
                    continue
                sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
                stats["applied"] += 1
                report["applied"].append({**card, "set_code": code, "image_url": image})
            report["sets"][code] = dict(stats)
            print(code, dict(stats), flush=True)
    report["summary"] = {
        "packs": len(TARGETS),
        "applied": len(report["applied"]),
        "unresolved": len(report["unresolved"]),
        "unresolved_by_reason": dict(Counter(row["reason"] for row in report["unresolved"])),
    }
    out = Path("_audit_out/refill_all70_daldagury_safe.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
