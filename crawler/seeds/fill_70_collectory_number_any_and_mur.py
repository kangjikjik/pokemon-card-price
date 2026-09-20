"""70팩 미등록 이미지를 Collectory 번호·등급 기준으로 채우고 MUR 이미지를 교체한다."""
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
from fill_all_70_missing_daldagury_exact import TARGETS
from kr_sets import COLLECTORY_IDS


def number_key(value: str | None) -> str:
    match = re.match(r"\s*0*(\d+)\s*/\s*0*(\d+)", value or "")
    return f"{int(match.group(1)):03d}/{int(match.group(2))}" if match else ""


def rarity_key(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").upper())


def valid_image(client: httpx.Client, url: str) -> None:
    response = client.get(url)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as image:
        image.verify()


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    }
    report = {"policy": "Collectory card number + rarity; region unrestricted", "applied": [], "mur_replaced": [], "unresolved": [], "sets": {}}
    with httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code, collectory_id in TARGETS.items():
            if code not in sets or not COLLECTORY_IDS.get(code):
                continue
            source = client.get(f"https://collectory.cc/api/sets/{COLLECTORY_IDS[code]}/cards", timeout=90).json().get("cards") or []
            by_number = {}
            for row in source:
                by_number.setdefault(number_key(row.get("card_number")), []).append(row)
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            stats = Counter()
            for card in cards:
                if (card.get("image_url") or "").strip():
                    continue
                candidates = by_number.get(number_key(card.get("card_number")), [])
                same_rarity = [row for row in candidates if rarity_key(row.get("rarity")) == rarity_key(card.get("rarity"))]
                selected = same_rarity or candidates
                urls = []
                for row in selected:
                    url = row.get("cdn_image_url") or row.get("image_url") or ""
                    if url and url not in urls:
                        urls.append(url)
                if len(urls) != 1:
                    report["unresolved"].append({**card, "set_code": code, "reason": "multiple_or_missing_collectory_candidate", "candidate_urls": urls})
                    stats["unresolved"] += 1
                    continue
                image = urls[0]
                try:
                    valid_image(client, image)
                except Exception as exc:
                    report["unresolved"].append({**card, "set_code": code, "reason": f"invalid_image:{exc}", "candidate_url": image})
                    stats["invalid_image"] += 1
                    continue
                sb.table("cards").update({"image_url": image}).eq("id", card["id"]).execute()
                report["applied"].append({**card, "set_code": code, "image_url": image})
                stats["applied"] += 1
            report["sets"][code] = dict(stats)

        overrides = [
            (3141, "https://cdn.collectory.cc/cards/kr/BS2025015/250_193.webp", "메가망나뇽 ex MUR"),
            (9733, None, "메가개굴닌자 ex MUR"),
        ]
        # 개굴닌자는 Collectory의 카드번호·등급 일치 이미지가 있으면 사용한다.
        mg5a_source = client.get(f"https://collectory.cc/api/sets/{COLLECTORY_IDS['MG5a']}/cards", timeout=90).json().get("cards") or []
        greninja = [
            row for row in mg5a_source
            if number_key(row.get("card_number")) == "120/83" and rarity_key(row.get("rarity")) == "MUR"
        ]
        if greninja:
            overrides[1] = (9733, greninja[0].get("cdn_image_url") or greninja[0].get("image_url"), "메가개굴닌자 ex MUR")
        for card_id, image, label in overrides:
            if not image:
                report["unresolved"].append({"card_id": card_id, "reason": "mur_collectory_image_not_found", "label": label})
                continue
            try:
                valid_image(client, image)
                sb.table("cards").update({"image_url": image}).eq("id", card_id).execute()
                report["mur_replaced"].append({"card_id": card_id, "label": label, "image_url": image})
            except Exception as exc:
                report["unresolved"].append({"card_id": card_id, "reason": f"mur_invalid_image:{exc}", "label": label, "candidate_url": image})

    report["summary"] = {"packs": len(TARGETS), "applied": len(report["applied"]), "mur_replaced": len(report["mur_replaced"]), "unresolved": len(report["unresolved"]), "unresolved_by_reason": dict(Counter(row["reason"] for row in report["unresolved"]))}
    out = Path("_audit_out/fill_70_collectory_number_any_and_mur.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
