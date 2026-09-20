"""8개 구세트의 미등록 이미지를 Collectory 이름·등급 기준으로 채운다."""
from __future__ import annotations

import io
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase
from kr_sets import COLLECTORY_IDS

TARGETS = ["S5F", "S3H", "S1W", "SM12a", "S2R", "S4B", "S5S", "SM9a"]
SUFFIX_RE = re.compile(r"(?:ex|gx|vmax|vstar|v)+$", re.I)


def name_key(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", (value or "").casefold())
    value = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", value)
    value = re.sub(r"[^0-9a-z가-힣]", "", value)
    value = SUFFIX_RE.sub("", value)
    return value


def rarity_key(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").upper())


def main() -> None:
    sb = get_supabase()
    sets = {
        row["set_code"]: row
        for row in sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", TARGETS).execute().data or []
    }
    report = {"policy": "ignore card number; require rarity and non-distinct name match", "applied": [], "unresolved": [], "sets": {}}
    with httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for code in TARGETS:
            source_set_id = COLLECTORY_IDS.get(code)
            if code not in sets or not source_set_id:
                continue
            source = client.get(f"https://collectory.cc/api/sets/{source_set_id}/cards", timeout=90).json().get("cards") or []
            by_key = {}
            for row in source:
                if row.get("region") != "kr":
                    continue
                key = (name_key(row.get("name_ko")), rarity_key(row.get("rarity")))
                by_key.setdefault(key, []).append(row)
            cards = sb.table("cards").select("id,card_number,name_kr,rarity,image_url").eq("set_id", sets[code]["id"]).execute().data or []
            stats = Counter()
            for card in cards:
                if (card.get("image_url") or "").strip():
                    continue
                candidates = by_key.get((name_key(card.get("name_kr")), rarity_key(card.get("rarity"))), [])
                urls = list(dict.fromkeys((row.get("cdn_image_url") or "") for row in candidates if "/cards/kr/" in (row.get("cdn_image_url") or "")))
                if not candidates:
                    report["unresolved"].append({**card, "set_code": code, "reason": "name_or_rarity_mismatch"})
                    stats["name_or_rarity_mismatch"] += 1
                    continue
                if len(urls) != 1:
                    report["unresolved"].append({**card, "set_code": code, "reason": "multiple_collectory_candidates", "candidate_names": [row.get("name_ko") for row in candidates], "candidate_urls": urls})
                    stats["multiple_collectory_candidates"] += 1
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
                report["applied"].append({**card, "set_code": code, "image_url": image, "collectory_name": candidates[0].get("name_ko")})
                stats["applied"] += 1
            report["sets"][code] = dict(stats)
            print(code, dict(stats), flush=True)
    report["summary"] = {
        "packs": len(TARGETS),
        "applied": len(report["applied"]),
        "unresolved": len(report["unresolved"]),
        "unresolved_by_reason": dict(Counter(row["reason"] for row in report["unresolved"])),
    }
    out = Path("_audit_out/fill_8_sets_collectory_name_rarity.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
