"""스톰 에메랄다 공식 이미지와 151 RM Collectory 이미지를 적용한다."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

OFFICIAL_REPORT = Path("_audit_out/all_80_official_image_check.json")
SV2A_SET = "1d7e469a-95d9-4710-a9c3-09ad381b40cc"


def base_number(value: str | None) -> str:
    match = re.match(r"\s*0*(\d+)\s*/\s*(\d+)", value or "")
    return f"{int(match.group(1)):03d}/{match.group(2)}" if match else ""


def main() -> None:
    sb = get_supabase()
    report = {"official_applied": [], "collectory_applied": [], "unresolved": []}
    with httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        # 공식 검증 보고서에서 카드 번호·이름이 이미 matched 된 스톰 에메랄다만 적용한다.
        official = json.loads(OFFICIAL_REPORT.read_text(encoding="utf-8"))
        storm = [row for row in official if row.get("set_code") == "MG7" and row.get("status") == "matched"]
        for row in storm:
            response = client.get(row["official_image_url"])
            if response.status_code >= 400 or len(response.content) < 200:
                report["unresolved"].append({
                    "set_code": "MG7",
                    "card_id": row["card_id"],
                    "card_number": row["card_number"],
                    "name_kr": row["name_kr"],
                    "reason": f"official_image_http_{response.status_code}",
                    "official_image_url": row["official_image_url"],
                })
                continue
            updated = sb.table("cards").update({"image_url": row["official_image_url"]}).eq("id", row["card_id"]).execute().data or []
            if updated:
                report["official_applied"].append({
                    "card_id": row["card_id"],
                    "card_number": row["card_number"],
                    "name_kr": row["name_kr"],
                    "image_url": row["official_image_url"],
                })

        # 인페르노X의 116/080은 공식 M3_116 이미지가 116/080 유카리로 표시되어
        # DB의 메가리자몽X ex와 내용이 충돌한다. 잘못된 이미지는 적용하지 않는다.
        report["unresolved"].append({
            "set_code": "MG4",
            "card_id": 3309,
            "card_number": "116/080",
            "name_kr": "메가리자몽X ex",
            "reason": "공식 116/080 이미지가 유카리로 표시되어 DB 카드명과 불일치",
            "official_candidate": "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M3/M3_116.png",
        })

        sv2a_rows = client.get(f"https://collectory.cc/api/sets/{SV2A_SET}/cards").json().get("cards") or []
        candidates = {
            (base_number(row.get("card_number")), (row.get("rarity") or "").upper()): row
            for row in sv2a_rows
            if row.get("region") == "kr"
        }
        sv2a_set_id = (sb.table("card_sets").select("id").eq("set_code", "SV2a").single().execute().data or {})["id"]
        cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sv2a_set_id).execute().data or []
        for card in cards:
            if (card.get("rarity") or "").upper() != "RM" or (card.get("image_url") or "").strip():
                continue
            source = candidates.get((base_number(card.get("card_number")), "R"))
            image = (source or {}).get("cdn_image_url") or ""
            if not image:
                report["unresolved"].append({**card, "reason": "collectory_R_image_not_found"})
                continue
            client.get(image).raise_for_status()
            updated = sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute().data or []
            if updated:
                report["collectory_applied"].append({
                    "card_id": card["id"],
                    "card_number": card["card_number"],
                    "name_kr": card["name_kr"],
                    "rarity": "RM",
                    "collectory_rarity": source.get("rarity"),
                    "image_url": image,
                })

    out = Path("_audit_out/official_storm_collectory_151_apply.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "official_applied": len(report["official_applied"]),
        "collectory_applied": len(report["collectory_applied"]),
        "unresolved": report["unresolved"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
