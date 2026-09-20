"""사용자가 지정한 6장의 달다구리 이름·이미지를 적용한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

TARGETS = {
    "MG4a": (4, {
        "209/193": ("가라르 가로막구리", 9786),
        "213/193": ("스핀로토무", 9788),
        "234/193": ("피카츄 ex", 9787),
    }),
    "SV4a": (14, {
        "347/190": ("뮤 ex", 10244),
        "236/190": ("피카츄", 10569),
        "249/190": ("빠르모트", 10582),
    }),
}


def medium(url: str) -> str:
    return url.replace("_thumb.webp", "_medium.webp")


def main() -> None:
    sb = get_supabase()
    report = []
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, (source_set_id, targets) in TARGETS.items():
            rows = client.get(f"https://api.daldagury.com/tcg/sets/{source_set_id}/cards?limit=500").json()["resultData"]["data"]
            source_by_number = {row.get("numberInSet"): row for row in rows}
            for card_number, (expected_name, card_id) in targets.items():
                source = source_by_number.get(card_number)
                if not source:
                    raise RuntimeError(f"{code} {card_number}: 달다구리 원본 없음")
                image = medium(source["thumbnailUrl"])
                response = client.get(image)
                response.raise_for_status()
                db_row = sb.table("cards").select("id,card_number,name_kr,name_jp,name_en,rarity").eq("id", card_id).single().execute().data
                updated = sb.table("cards").update({
                    "name_kr": expected_name,
                    "name_jp": expected_name,
                    "name_en": expected_name,
                    "image_url": image,
                }).eq("id", card_id).execute().data or []
                report.append({
                    "set_code": code,
                    "card_id": card_id,
                    "card_number": card_number,
                    "old": db_row,
                    "new_name": expected_name,
                    "daldagury_name": source.get("nameKo"),
                    "daldagury_rarity": source.get("lowestRarity"),
                    "image_url": image,
                    "updated": bool(updated),
                })
    Path("_audit_out").mkdir(exist_ok=True)
    Path("_audit_out/fix_selected_daldagury_names_images.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
