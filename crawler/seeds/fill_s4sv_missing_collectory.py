"""샤이니스타 V의 미등록 이미지를 Collectory 한국판 CDN에서 채운다."""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

SET_CODE = "S4SV"
COLLECTORY_SET_ID = "05273182-6ced-4135-95ad-57070ce7c8e5"


def number_key(value: str | None) -> str:
    match = re.match(r"\s*0*(\d+)\s*/\s*0*(\d+)", value or "")
    return f"{int(match.group(1)):03d}/{int(match.group(2))}" if match else ""


def rarity_key(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip()).upper()


def main() -> None:
    sb = get_supabase()
    set_row = sb.table("card_sets").select("id,set_code,name_kr").eq("set_code", SET_CODE).single().execute().data
    source = httpx.get(f"https://collectory.cc/api/sets/{COLLECTORY_SET_ID}/cards", timeout=90).json().get("cards") or []
    source_by_key = {
        (number_key(row.get("card_number")), rarity_key(row.get("rarity"))): row
        for row in source
        if row.get("region") == "kr"
    }
    cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", set_row["id"]).execute().data or []
    applied = []
    unresolved = []
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for card in cards:
            if (card.get("image_url") or "").strip():
                continue
            source_card = source_by_key.get((number_key(card.get("card_number")), rarity_key(card.get("rarity"))))
            image = (source_card or {}).get("cdn_image_url") or ""
            if not image or "/cards/kr/" not in image:
                unresolved.append({**card, "reason": "collectory_kr_image_not_found"})
                continue
            try:
                response = client.get(image)
                response.raise_for_status()
                with Image.open(io.BytesIO(response.content)) as img:
                    img.verify()
            except Exception as exc:
                unresolved.append({**card, "reason": f"invalid_image:{exc}", "candidate_url": image})
                continue
            sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
            applied.append({
                **card,
                "image_url": image,
                "collectory_name": source_card.get("name_ko"),
                "collectory_rarity": source_card.get("rarity"),
            })
    report = {
        "set_code": SET_CODE,
        "collectory_set_id": COLLECTORY_SET_ID,
        "applied": applied,
        "unresolved": unresolved,
        "summary": {"applied": len(applied), "unresolved": len(unresolved)},
    }
    out = Path("_audit_out/fill_s4sv_missing_collectory.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if unresolved:
        print(json.dumps(unresolved, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
