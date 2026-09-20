"""다음 20개 세트에서 달다구리 미해결 카드의 Collectory 한국판 이미지를 보완."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from kr_sets import KR_SETS
from utils.db import get_supabase


TARGETS = {
    "MG7", "S10a", "S9a", "S9", "S8", "S8a", "S8b", "S7F", "CEL",
    "S7R", "S7D", "S6H", "S6G", "S6L", "S5F", "S5S", "S5P", "S4SV",
    "S4B", "S3H",
}


def candidates(bs_code: str, card_number: str, rarity: str) -> list[str]:
    compact = re.sub(r"\s+", "", card_number or "")
    match = re.search(r"(\d+)/(\d+)", compact)
    if not match:
        return []
    stem = f"{int(match.group(1)):03d}_{int(match.group(2)):03d}"
    base = bs_code.removesuffix("-kr")
    return [
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}{rarity}.webp",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}{rarity}.jpg",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}.webp",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}.jpg",
    ]


def main() -> None:
    sb = get_supabase()
    metas = {
        x.code: x
        for x in KR_SETS
        if x.code in TARGETS
    }
    sets = {
        x["set_code"]: x
        for x in sb.table("card_sets")
        .select("id,set_code")
        .in_("set_code", list(TARGETS))
        .execute()
        .data
        or []
    }
    report = {"updated": [], "unresolved": []}
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for code in TARGETS:
            rows = (
                sb.table("cards")
                .select("id,card_number,name_kr,rarity,image_url")
                .eq("set_id", sets[code]["id"])
                .execute()
                .data
                or []
            )
            for card in rows:
                if card.get("image_url"):
                    continue
                found = None
                for url in candidates(
                    metas[code].bs_code,
                    card.get("card_number") or "",
                    card.get("rarity") or "",
                ):
                    try:
                        response = client.get(url)
                        if response.status_code == 200 and response.headers.get(
                            "content-type", ""
                        ).startswith("image/"):
                            found = url
                            break
                    except Exception:
                        continue
                if found:
                    sb.table("cards").update({"image_url": found}).eq(
                        "id", card["id"]
                    ).execute()
                    report["updated"].append(
                        {"set_code": code, "card_id": card["id"], "image_url": found}
                    )
                else:
                    report["unresolved"].append(
                        {
                            "set_code": code,
                            "card_id": card["id"],
                            "card_number": card.get("card_number"),
                            "name_kr": card.get("name_kr"),
                            "rarity": card.get("rarity"),
                        }
                    )
    Path("_audit_out/legacy_20_collectory_fallback.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: len(value) for key, value in report.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
