"""최신 MEGA 6개 세트의 DB 카드를 달다구리 한국판 이미지로 채웁니다."""
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


# 프로젝트 세트 코드 -> 달다구리 한국판 세트 ID
TARGETS = {
    "MG5a": 2239,  # M4 닌자스피너
    "MG5": 284,  # M3 니힐제로
    "MG4a": 4,  # M2a MEGA 드림 ex
    "MG4": 5,  # M2 인페르노X
    "MG3a": 283,  # M1S 메가심포니아
    "MG3": 282,  # M1L 메가브레이브
}
DALDAGURY_API = "https://api.daldagury.com"
REPORT = Path("_audit_out/mega6_daldagury_apply.json")


def number_key(value: str | None) -> int | None:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else None


def fetch_source_cards(client: httpx.Client, set_id: int) -> dict[int, dict]:
    response = client.get(f"{DALDAGURY_API}/tcg/sets/{set_id}/cards?limit=300")
    response.raise_for_status()
    body = response.json()
    rows = body.get("resultData", {}).get("data", [])
    return {
        number_key(row.get("numberInSet") or row.get("cardNumber")): row
        for row in rows
        if number_key(row.get("numberInSet") or row.get("cardNumber")) is not None
        and row.get("thumbnailUrl")
    }


def medium_url(thumbnail_url: str) -> str:
    return thumbnail_url.replace("_thumb.webp", "_medium.webp")


def main() -> None:
    load_dotenv()
    sb = get_supabase()
    results: list[dict] = []
    summary: dict[str, dict] = {}

    with httpx.Client(
        timeout=httpx.Timeout(20.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "pokemon-card-price/1.0"},
    ) as client:
        for project_code, daldagury_set_id in TARGETS.items():
            set_row = (
                sb.table("card_sets")
                .select("id,set_code,name_kr")
                .eq("set_code", project_code)
                .single()
                .execute()
                .data
            )
            if not set_row:
                raise RuntimeError(f"DB에서 세트를 찾지 못했습니다: {project_code}")

            source_cards = fetch_source_cards(client, daldagury_set_id)
            cards = (
                sb.table("cards")
                .select("id,card_number,name_kr,rarity,image_url")
                .eq("set_id", set_row["id"])
                .execute()
                .data
                or []
            )
            counts = {"checked": len(cards), "updated": 0, "unchanged": 0, "unresolved": 0}

            for card in cards:
                number = number_key(card.get("card_number"))
                source = source_cards.get(number) if number is not None else None
                if not source:
                    counts["unresolved"] += 1
                    results.append(
                        {
                            "set_code": project_code,
                            "card_id": card["id"],
                            "card_number": card.get("card_number"),
                            "status": "unresolved",
                            "reason": "source_card_number_not_found",
                        }
                    )
                    continue

                url = medium_url(source["thumbnailUrl"])
                try:
                    response = client.get(url)
                    content_type = response.headers.get("content-type", "")
                    if response.status_code != 200 or not content_type.startswith("image/"):
                        raise RuntimeError(f"http_{response.status_code}_{content_type}")
                except Exception as exc:
                    counts["unresolved"] += 1
                    results.append(
                        {
                            "set_code": project_code,
                            "card_id": card["id"],
                            "card_number": card.get("card_number"),
                            "status": "unresolved",
                            "reason": str(exc),
                            "candidate_url": url,
                        }
                    )
                    continue

                old_url = card.get("image_url")
                if old_url == url:
                    status = "unchanged"
                    counts["unchanged"] += 1
                else:
                    sb.table("cards").update({"image_url": url}).eq(
                        "id", card["id"]
                    ).execute()
                    status = "updated"
                    counts["updated"] += 1

                results.append(
                    {
                        "set_code": project_code,
                        "card_id": card["id"],
                        "card_number": card.get("card_number"),
                        "name_kr": card.get("name_kr"),
                        "rarity": card.get("rarity"),
                        "old_image_url": old_url,
                        "image_url": url,
                        "source_set_id": daldagury_set_id,
                        "source_card_id": source.get("cardId"),
                        "status": status,
                    }
                )
                print(f"[{status}] {project_code} {card.get('card_number')} card_id={card['id']}")

            summary[project_code] = {
                "daldagury_set_id": daldagury_set_id,
                **counts,
            }

    report = {
        "source": "daldagury",
        "sets": summary,
        "total": {
            key: sum(item[key] for item in summary.values())
            for key in ("checked", "updated", "unchanged", "unresolved")
        },
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**summary, "total": report["total"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
