"""어비스아이(MG6) 카드 이미지를 달다구리 한국판 이미지로 채웁니다."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.db import get_supabase


SET_CODE = "MG6"
DALDAGURY_BASE = (
    "https://s3.ap-northeast-2.amazonaws.com/"
    "prod.daldagury.com/uploads/tcg/pokemon/m5/resized"
)
REPORT = Path("_audit_out/mg6_daldagury_apply.json")


def card_num(value: str | None) -> int | None:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else None


def image_url(number: int) -> str:
    return f"{DALDAGURY_BASE}/bs2026004{number:03d}_medium.webp"


def main() -> None:
    load_dotenv()
    sb = get_supabase()
    set_row = (
        sb.table("card_sets")
        .select("id,set_code,name_kr")
        .eq("set_code", SET_CODE)
        .single()
        .execute()
        .data
    )
    if not set_row:
        raise RuntimeError("card_sets에서 MG6를 찾지 못했습니다.")

    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,rarity,image_url")
        .eq("set_id", set_row["id"])
        .execute()
        .data
        or []
    )

    results: list[dict] = []
    with httpx.Client(
        timeout=httpx.Timeout(20.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "pokemon-card-price/1.0"},
    ) as client:
        for card in cards:
            number = card_num(card.get("card_number"))
            if number is None:
                results.append(
                    {
                        "card_id": card["id"],
                        "status": "unresolved",
                        "reason": "invalid_card_number",
                    }
                )
                continue

            url = image_url(number)
            try:
                response = client.get(url)
                content_type = response.headers.get("content-type", "")
                if response.status_code != 200 or not content_type.startswith("image/"):
                    results.append(
                        {
                            "card_id": card["id"],
                            "card_number": card.get("card_number"),
                            "status": "unresolved",
                            "reason": f"http_{response.status_code}_{content_type}",
                            "candidate_url": url,
                        }
                    )
                    continue
            except Exception as exc:
                results.append(
                    {
                        "card_id": card["id"],
                        "card_number": card.get("card_number"),
                        "status": "unresolved",
                        "reason": f"{type(exc).__name__}: {exc}",
                        "candidate_url": url,
                    }
                )
                continue

            old_url = card.get("image_url")
            if old_url == url:
                status = "unchanged"
            else:
                sb.table("cards").update({"image_url": url}).eq(
                    "id", card["id"]
                ).execute()
                status = "updated"

            results.append(
                {
                    "card_id": card["id"],
                    "card_number": card.get("card_number"),
                    "name_kr": card.get("name_kr"),
                    "rarity": card.get("rarity"),
                    "old_image_url": old_url,
                    "image_url": url,
                    "status": status,
                }
            )
            print(
                f"[{status}] {card.get('card_number')} "
                f"{card.get('rarity')} card_id={card['id']}"
            )

    summary = {
        "set_code": SET_CODE,
        "source": "daldagury",
        "source_set_id": 2569,
        "cards_checked": len(cards),
        "updated": sum(r["status"] == "updated" for r in results),
        "unchanged": sum(r["status"] == "unchanged" for r in results),
        "unresolved": sum(r["status"] == "unresolved" for r in results),
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
