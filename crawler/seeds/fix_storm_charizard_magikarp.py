"""스톰 에메랄다 오케이징 및 Collectory 지정 카드 이미지 적용."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def main() -> None:
    sb = get_supabase()
    official_storm_url = "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M6/M6_085.png"
    collectory_charizard_url = "https://cdn.collectory.cc/cards/kr/BS2025014/116_080.webp"
    collectory_magikarp_url = "https://cdn.collectory.cc/cards/kr/M-P/040_M-P.webp"
    report = {"updated": [], "url_checks": []}

    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for label, url in (
            ("official_storm_okeking", official_storm_url),
            ("collectory_charizard", collectory_charizard_url),
            ("collectory_magikarp", collectory_magikarp_url),
        ):
            response = client.get(url)
            report["url_checks"].append({
                "label": label,
                "url": url,
                "status_code": response.status_code,
                "bytes": len(response.content),
            })

        updates = [
            (9719, {
                "name_kr": "오케이징",
                "name_jp": "오케이징",
                "name_en": "오케이징",
                "image_url": official_storm_url,
            }),
            (3309, {"image_url": collectory_charizard_url}),
            (9150, {"image_url": collectory_magikarp_url}),
        ]
        for card_id, values in updates:
            rows = sb.table("cards").update(values).eq("id", card_id).execute().data or []
            report["updated"].append({"card_id": card_id, "values": values, "updated": bool(rows)})

    out = Path("_audit_out/fix_storm_charizard_magikarp.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
