"""VSTAR 유니버스·패러다임 트리거 지정 카드 보정."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

REPORT = Path("_audit_out/fix_vstar_paradigm_daldagury.json")
VSTAR = {
    "205/172": (10795, "피카츄"),
    "042/172": (10796, "제라오라 VSTAR"),
}
PARADIGM = {
    "034/098": 4405,
    "115/098": 4429,
}


def medium(url: str) -> str:
    return url.replace("_thumb.webp", "_medium.webp")


def delete_card(sb, card_id: int) -> None:
    for table in ("prices_kr", "prices_jp"):
        sb.table(table).delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main() -> None:
    sb = get_supabase()
    report = {"updated": [], "deleted": [], "source": "daldagury_only"}
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        vstar_rows = client.get("https://api.daldagury.com/tcg/sets/18/cards?limit=500").json()["resultData"]["data"]
        vstar_by_number = {row.get("numberInSet"): row for row in vstar_rows}
        for number, (card_id, name) in VSTAR.items():
            source = vstar_by_number[number]
            image = medium(source["thumbnailUrl"])
            client.get(image).raise_for_status()
            updated = sb.table("cards").update({
                "name_kr": name,
                "name_jp": name,
                "name_en": name,
                "image_url": image,
            }).eq("id", card_id).execute().data or []
            report["updated"].append({"card_id": card_id, "card_number": number, "name": name, "image_url": image, "updated": bool(updated)})

        deleted_row = sb.table("cards").select("id,card_number,name_kr,rarity").eq("id", 10884).single().execute().data
        delete_card(sb, 10884)
        report["deleted"].append(deleted_row)

        paradigm_rows = client.get("https://api.daldagury.com/tcg/sets/268/cards?limit=500").json()["resultData"]["data"]
        paradigm_by_number = {row.get("numberInSet"): row for row in paradigm_rows}
        for number, card_id in PARADIGM.items():
            source = paradigm_by_number[number]
            image = medium(source["thumbnailUrl"])
            client.get(image).raise_for_status()
            card = sb.table("cards").select("name_kr").eq("id", card_id).single().execute().data
            updated = sb.table("cards").update({"image_url": image}).eq("id", card_id).execute().data or []
            report["updated"].append({"card_id": card_id, "card_number": number, "name": card.get("name_kr"), "image_url": image, "updated": bool(updated), "ignore_source_suffix": True})

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
